"""Conservative source admission for a semantic-defect benchmark threat.

This is an AST policy filter, not a Python sandbox or a proof against obfuscation,
side channels, hostile generated code, or hidden-data access. OS isolation and
restricted candidate filesystem visibility remain separate requirements.
"""
from __future__ import annotations

import ast
import hashlib

VERSION = "semantic-defect-admission-v1"
ALLOWED_IMPORTS = {
    "__future__": {"annotations"},
    "math": set("acos acosh asin asinh atan atan2 atanh ceil comb copysign cos cosh degrees dist e erf erfc exp expm1 fabs factorial floor fmod frexp fsum gamma gcd hypot inf isclose isfinite isinf isnan isqrt ldexp lgamma log log10 log1p log2 modf nan nextafter perm pi pow prod radians remainder sin sinh sqrt tan tanh tau trunc ulp lcm exp2 cbrt".split()),
    "cmath": set("acos acosh asin asinh atan atanh cos cosh e exp inf infj isclose isfinite isinf isnan log log10 nan nanj phase pi polar rect sin sinh sqrt tan tanh tau".split()),
    "typing": set("Any Callable Collection Counter DefaultDict Deque Dict FrozenSet Iterable Iterator List Mapping MutableMapping Optional Sequence Set Tuple Union Literal NamedTuple TypeVar Generic".split()),
    "collections": set("Counter defaultdict deque OrderedDict ChainMap namedtuple UserDict UserList UserString".split()),
    "itertools": set("accumulate chain combinations combinations_with_replacement compress count cycle dropwhile filterfalse groupby islice pairwise permutations product repeat starmap takewhile tee zip_longest".split()),
    "functools": set("cache lru_cache reduce partial cmp_to_key total_ordering wraps".split()),
    "operator": set("abs add and_ concat contains countOf eq floordiv ge getitem gt index indexOf inv invert is_ is_not le length_hint lshift lt matmul mod mul ne neg not_ or_ pos pow rshift sub truediv truth xor itemgetter".split()),
    "heapq": set("heapify heappop heappush heappushpop heapreplace merge nlargest nsmallest".split()),
    "bisect": set("bisect bisect_left bisect_right insort insort_left insort_right".split()),
    "re": set("compile escape findall finditer fullmatch match search split sub subn A ASCII DEBUG DOTALL I IGNORECASE L LOCALE M MULTILINE NOFLAG S U UNICODE VERBOSE X".split()),
    "string": set("ascii_letters ascii_lowercase ascii_uppercase digits hexdigits octdigits punctuation printable whitespace capwords".split()),
    "statistics": set("mean fmean geometric_mean harmonic_mean median median_low median_high median_grouped mode multimode quantiles pstdev pvariance stdev variance correlation covariance linear_regression".split()),
    "fractions": {"Fraction"},
    "decimal": set("Decimal Context getcontext localcontext ROUND_CEILING ROUND_DOWN ROUND_FLOOR ROUND_HALF_DOWN ROUND_HALF_EVEN ROUND_HALF_UP ROUND_UP ROUND_05UP".split()),
    "hashlib": set("md5 sha1 sha224 sha256 sha384 sha512 sha3_224 sha3_256 sha3_384 sha3_512 shake_128 shake_256 blake2b blake2s new algorithms_available algorithms_guaranteed".split()),
}
BANNED_NAMES = set("open exec eval compile __import__ input print breakpoint globals locals vars dir getattr setattr delattr hasattr help id exit quit license copyright credits memoryview".split())
# Qualified names below are rejected even if reached through a benign alias.
BANNED_ATTRIBUTES = set("system popen spawn fork forkpty execv execve execl execlp execvp execvpe environ getenv putenv unsetenv read read1 readline readlines write writelines open close load loads dump dumps save savez save_load fromfile tofile memmap ctypes ctypeslib f2py socket connect request urlopen get_type_hints attrgetter methodcaller format format_map file_digest modules currentframe stack getframeinfo mro".split())
SENSITIVE_DUNDER_LITERALS = {"__globals__", "__builtins__", "__subclasses__", "__class__", "__code__", "__dict__", "__getattribute__", "__import__"}
ALLOWED_TOP_LEVEL = (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.Assign, ast.AnnAssign)


def admit_source(source: str, entry_point: str | None = None, *, max_chars: int = 50000) -> dict:
    """Return an auditable admission decision without importing/executing source."""
    reasons = []

    def reject(code, node=None, detail=""):
        item = {"code": code, "line": getattr(node, "lineno", None), "detail": detail}
        if item not in reasons:
            reasons.append(item)

    if not isinstance(source, str):
        return {"version": VERSION, "admitted": False, "reasons": [{"code": "source_not_text", "line": None, "detail": ""}], "source_sha256": None}
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if len(source) > max_chars:
        reject("source_size_limit", detail=str(max_chars))
        return {"version": VERSION, "admitted": False, "reasons": reasons, "source_sha256": digest, "entry_point": entry_point}
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, MemoryError, RecursionError) as exc:
        reject("syntax_or_parse_error", detail=type(exc).__name__)
        return {"version": VERSION, "admitted": False, "reasons": reasons, "source_sha256": digest, "entry_point": entry_point}
    imports = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name not in ALLOWED_IMPORTS:
                    reject("import_not_allowed", node, alias.name)
                else:
                    imports[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level or node.module not in ALLOWED_IMPORTS:
                reject("import_not_allowed", node, ("." * node.level) + str(node.module))
            else:
                for alias in node.names:
                    if alias.name not in ALLOWED_IMPORTS[node.module]:
                        reject("import_member_not_allowed", node, node.module + "." + alias.name)
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            continue
        if not isinstance(node, ALLOWED_TOP_LEVEL):
            reject("top_level_statement_not_allowed", node, type(node).__name__)
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
            try:
                ast.literal_eval(node.value)
            except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
                reject("top_level_value_not_literal", node)
    functions = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
    if entry_point is not None and functions.count(entry_point) != 1:
        reject("entry_point_missing_or_repeated", detail=entry_point)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and (node.id in BANNED_NAMES or node.id.startswith("__")):
            reject("forbidden_name", node, node.id)
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("_") or node.attr in BANNED_ATTRIBUTES:
                reject("forbidden_attribute", node, node.attr)
            if isinstance(node.value, ast.Name) and node.value.id in imports:
                module = imports[node.value.id]
                if node.attr not in ALLOWED_IMPORTS[module]:
                    reject("module_attribute_not_allowed", node, module + "." + node.attr)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            reject("external_scope_mutation_not_allowed", node)
        elif isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef, ast.Await, ast.AsyncFor, ast.AsyncWith)):
            reject("unsupported_execution_construct", node, type(node).__name__)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "type" and (len(node.args) != 1 or node.keywords):
            reject("dynamic_type_construction_not_allowed", node)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and any(token in node.value for token in SENSITIVE_DUNDER_LITERALS):
            # Conservative literal guard; obfuscated strings are not proven safe.
            reject("dunder_string_not_allowed", node)
    return {"version": VERSION, "admitted": not reasons, "reasons": reasons, "source_sha256": digest,
            "entry_point": entry_point, "scope": "Conservative AST admission for semantic-defect study only; not a security sandbox or proof of gold isolation."}
