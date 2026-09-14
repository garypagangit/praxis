"""Independent policy examples; source snippets are parsed, never executed."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
from execution_admission import admit_source

CASES = [
    ("pure_identity", "def f(x):\n    return x\n", True),
    ("pure_helper", "def helper(x):\n    return x+1\ndef f(x):\n    return helper(x)\n", True),
    ("math_alias", "import math as m\ndef f(x):\n    return m.sqrt(x)\n", True),
    ("from_math", "from math import sqrt as root\ndef f(x):\n    return root(x)\n", True),
    ("typing_annotation", "from typing import List\ndef f(x: List[int]) -> int:\n    return sum(x)\n", True),
    ("hashlib_digest", "import hashlib\ndef f(x):\n    return hashlib.md5(x.encode()).hexdigest()\n", True),
    ("regular_expression", "import re\ndef f(x):\n    return re.findall('[a-z]', x)\n", True),
    ("data_type_query", "def f(x):\n    return type(x) == str\n", True),
    ("literal_global", "OFFSET=2\ndef f(x):\n    return x+OFFSET\n", True),
    ("literal_underscore_data", "def f(x):\n    return x.replace('  ', '__')\n", True),
    ("resource_bound_still_required", "def f(x):\n    while True:\n        x += 1\n", True),
    ("open_direct", "def f(x):\n    return open(x).read()\n", False),
    ("open_alias", "def f(x):\n    alias=open\n    return alias(x)\n", False),
    ("eval_expression", "def f(x):\n    return eval(x)\n", False),
    ("exec_dynamic", "def f(x):\n    exec(x)\n    return 1\n", False),
    ("dynamic_import", "def f(x):\n    return __import__('os')\n", False),
    ("os_environment", "import os\ndef f(x):\n    return os.environ\n", False),
    ("network_import", "import socket\ndef f(x):\n    return socket.socket()\n", False),
    ("path_import", "from pathlib import Path\ndef f(x):\n    return Path(x).read_text()\n", False),
    ("inspect_stack", "import inspect\ndef f(x):\n    return inspect.stack()\n", False),
    ("dunder_attribute", "def f(x):\n    return x.__class__\n", False),
    ("private_module_attribute", "import math\ndef f(x):\n    return math._secret\n", False),
    ("globals_reference", "def f(x):\n    return globals()\n", False),
    ("getattr_dynamic", "def f(x):\n    return getattr(x, 'thing')\n", False),
    ("format_introspection", "def f(x):\n    return '{0.__class__}'.format(x)\n", False),
    ("operator_attrgetter", "from operator import attrgetter\ndef f(x):\n    return attrgetter('thing')(x)\n", False),
    ("typing_eval_hook", "import typing\ndef f(x):\n    return typing.get_type_hints(x)\n", False),
    ("star_import", "from math import *\ndef f(x):\n    return sqrt(x)\n", False),
    ("hashlib_file_digest", "import hashlib\ndef f(x):\n    return hashlib.file_digest(x, 'sha256')\n", False),
    ("top_level_execution", "def f(x):\n    return x\nf(1)\n", False),
    ("nested_forbidden_import", "def f(x):\n    import os\n    return x\n", False),
    ("dynamic_class", "def f(x):\n    return type('X', (), {})\n", False),
    ("global_mutation", "def f(x):\n    global state\n    state=x\n    return x\n", False),
    ("print_io", "def f(x):\n    print(x)\n    return x\n", False),
    ("missing_entrypoint", "def g(x):\n    return x\n", False),
    ("syntax_error", "def f(:\n", False),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline-jsonl", type=Path)
    args = parser.parse_args()
    results=[]
    for identifier,source,expected in CASES:
        actual=admit_source(source,"f")
        results.append({"id":identifier,"expected_admitted":expected,"actual_admitted":actual["admitted"],
                        "passed":actual["admitted"] is expected,"reason_codes":sorted({r["code"] for r in actual["reasons"]})})
    baseline=[]
    if args.baseline_jsonl:
        for line in args.baseline_jsonl.read_text(encoding="utf-8").splitlines():
            if not line.strip():continue
            row=json.loads(line)
            for variant in ("canonical_solution","buggy_solution"):
                source="\n".join([row.get("import", ""),row["declaration"],row[variant]])
                actual=admit_source(source,row["entry_point"])
                baseline.append({"task_id":row["task_id"],"variant":variant,"admitted":actual["admitted"],"reasons":actual["reasons"]})
    report={"completed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"scope":"AST parsing only; no candidate or benchmark program execution.",
            "validator_sha256":hashlib.sha256((Path(__file__).parent/'execution_admission.py').read_bytes()).hexdigest(),
            "control_script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"controls":len(results),"controls_passed":sum(r["passed"] for r in results),"results":results,
            "baseline_compatibility":{"source_sha256":hashlib.sha256(args.baseline_jsonl.read_bytes()).hexdigest() if args.baseline_jsonl else None,"variants_checked":len(baseline),"admitted":sum(r["admitted"] for r in baseline),"rejected":[r for r in baseline if not r["admitted"]]},
            "limitations":["AST checks do not prove safety or gold isolation.","Pure-looking infinite loops pass admission and require runtime resource limits.","Obfuscated access and malicious harness attacks are outside the evaluated semantic-defect threat.","Baseline rejections are disclosed; this audit does not silently exclude or amend study tasks."]}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({"controls":len(results),"passed":report['controls_passed'],"baseline_checked":len(baseline),"baseline_admitted":report['baseline_compatibility']['admitted']}))
    return 0 if report['controls_passed']==len(results) else 1


if __name__=='__main__':raise SystemExit(main())
