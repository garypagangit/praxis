"""Author-code interface qualification; not a completed efficacy comparison."""
import ast,hashlib,importlib.metadata,json,sys,typing
from pathlib import Path
HERE=Path(__file__).resolve().parent;OUT=Path('C:/w/px116_20261005')
result={'scope':'Interface/static qualification only. No comparator model generations or task-completion scores.'}
sys.path.insert(0,str(OUT/'AgentSpec/src'))
try:
    import rule as author_rule
    text='rule @check_install\ntrigger\n    Shell\ncheck\n    true\nenforce\n    stop\nend\n'
    parser=author_rule.AgentSpecParser(author_rule.CommonTokenStream(author_rule.AgentSpecLexer(author_rule.InputStream(text))))
    parser.program();assert parser.getNumberOfSyntaxErrors()==0
    rule=author_rule.Rule.from_text(text)
    result['AgentSpec']={'parse_ok':rule.event=='Shell','matching_trigger':rule.triggered('Shell','pip install numpy'),
        'nonmatching_trigger':rule.triggered('Other',''),'antlr_runtime':importlib.metadata.version('antlr4-python3-runtime'),
        'syntax_errors':0,'predicate_tested':'true (interface only)',
        'package_policy_requires_documented_grammar_and_predicate_adapter':True,
        'status':'RULE_INTERFACE_QUALIFIED_FULL_RUNTIME_NOT_YET_EVALUATED'}
except Exception as exc: result['AgentSpec']={'status':'INTERFACE_FAILED','error':repr(exc)}
source=OUT/'PackMonitor/HFuzzer/Framework/packmonitor_generate.py'
tree=ast.parse(source.read_text(encoding='utf-8'));cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='PackMonitor')
method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='make_grammar')
namespace={'List':typing.List}
exec(compile(ast.Module(body=[method],type_ignores=[]),str(source),'exec'),namespace)
grammar=namespace['make_grammar'](None,['numpy'])
undefined='NATATURAL_LANG' in grammar and 'NATATURAL_LANG:' not in grammar
content=source.read_bytes();fixed=content.replace(b'NATATURAL_LANG',b'NATURAL_LANG')
assert content.count(b'NATATURAL_LANG')==1
(OUT/'packmonitor_one_token_repair.py').write_bytes(fixed)
result['PackMonitor']={'source_sha256':hashlib.sha256(content).hexdigest(),'undefined_symbol_reproduced':undefined,
    'repair':'One NATATURAL_LANG token changed to NATURAL_LANG; author-code-derived repair, not unmodified official implementation',
    'repair_sha256':hashlib.sha256(fixed).hexdigest(),'status':'UPSTREAM_GRAMMAR_TYPO_REPRODUCED_REPAIR_PREPARED_NOT_FULLY_RUN'}
(HERE/'COMPARATOR_QUALIFICATION.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
