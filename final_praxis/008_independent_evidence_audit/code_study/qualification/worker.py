"""One isolated Linux process per task/program; imports are safe for comparator tests."""
from __future__ import annotations
import argparse
import ast
import contextlib
import copy
import hashlib
import io
import json
import math
import os
from pathlib import Path
import random
import signal
import sys
import time
import warnings
import numpy as np

class CaseTimeout(Exception): pass

def compare_output(entry_point, inp, output, expected, atol):
    """Pinned EvalPlus HumanEval predicates, with a Boolean result per input."""
    try:
        if entry_point == 'find_zero':
            residual=sum(coeff*math.pow(output,index) for index,coeff in enumerate(inp[0]))
            return bool(math.isfinite(residual) and abs(residual)<=atol)
        exact_match=output==expected
        is_floats=isinstance(expected,float) or (isinstance(expected,(list,tuple)) and bool(expected) and all(isinstance(x,float) for x in expected)) or (isinstance(expected,np.ndarray) and expected.dtype in (np.float64,np.float32))
        if atol==0 and is_floats: atol=1e-6
        if not exact_match and atol!=0:
            if type(output)!=type(expected): return False
            if isinstance(expected,(list,tuple)) and len(output)!=len(expected): return False
            return bool(np.allclose(output,expected,rtol=1e-7,atol=atol))
        return bool(exact_match)
    except CaseTimeout: raise
    except Exception: return False

def encode_value(value):
    if isinstance(value,np.generic): value=value.item()
    if value is None:return {'t':'none'}
    if type(value) is bool:return {'t':'bool','v':value}
    if type(value) is int:return {'t':'int','v':str(value)}
    if type(value) is float:return {'t':'float','v':value.hex()}
    if type(value) is str:return {'t':'str','v':value}
    if type(value) in (list,tuple):return {'t':type(value).__name__,'v':[encode_value(x) for x in value]}
    if type(value) is dict:return {'t':'dict','v':[[encode_value(k),encode_value(v)] for k,v in value.items()]}
    raise TypeError('unsupported_output_type:'+type(value).__name__)

def decode_value(value):
    tag=value['t']
    if tag=='none':return None
    if tag in ('bool','str'):return value['v']
    if tag=='int':return int(value['v'])
    if tag=='float':return float.fromhex(value['v'])
    if tag=='list':return [decode_value(x) for x in value['v']]
    if tag=='tuple':return tuple(decode_value(x) for x in value['v'])
    if tag=='dict':return {decode_value(k):decode_value(v) for k,v in value['v']}
    raise ValueError('unsupported_encoded_type')

def assert_isolation():
    if not sys.platform.startswith('linux') or os.geteuid()==0 or os.environ.get('PRAXIS_ISOLATED_EXECUTION')!='1':
        raise RuntimeError('Requires designated nonroot Linux isolation')
    if not Path('/.dockerenv').exists():raise RuntimeError('Docker marker missing')
    if set(os.listdir('/sys/class/net'))-{'lo'}:raise RuntimeError('Unexpected network interface')
    if any(key.startswith(('AWS_','AMAZON_')) for key in os.environ):raise RuntimeError('AWS environment must not be present')
    status=Path('/proc/self/status').read_text()
    if 'NoNewPrivs:\t1' not in status:raise RuntimeError('no-new-privileges missing')
    capabilities=next(line.split()[1] for line in status.splitlines() if line.startswith('CapEff:'))
    if int(capabilities,16):raise RuntimeError('Effective Linux capabilities remain')

@contextlib.contextmanager
def time_limit(seconds):
    def interrupt(signum,frame):raise CaseTimeout()
    old_handler=signal.signal(signal.SIGALRM,interrupt)
    old_timer=signal.setitimer(signal.ITIMER_REAL,max(0.001,seconds))
    started=time.monotonic()
    try:yield
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        signal.signal(signal.SIGALRM,old_handler)
        if old_timer[0]>0:signal.setitimer(signal.ITIMER_REAL,max(0.001,old_timer[0]-(time.monotonic()-started)),old_timer[1])

def load_program(code,entry_point):
    namespace={}
    with time_limit(5),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        exec(compile(code,'released-program','exec'),namespace)
    return namespace[entry_point]

class OriginalTrace(ast.NodeTransformer):
    def __init__(self):self.assertions=[]
    def visit_Assert(self,node):
        index=len(self.assertions);self.assertions.append({'assert_id':index,'line':node.lineno})
        arguments=[ast.Constant(index),ast.Lambda(args=ast.arguments(posonlyargs=[],args=[],vararg=None,kwonlyargs=[],kw_defaults=[],kwarg=None,defaults=[]),body=node.test)]
        if node.msg is not None:arguments.append(ast.Lambda(args=ast.arguments(posonlyargs=[],args=[],vararg=None,kwonlyargs=[],kw_defaults=[],kwarg=None,defaults=[]),body=node.msg))
        expression=ast.Expr(value=ast.Call(func=ast.Name(id='_record_assertion',ctx=ast.Load()),args=arguments,keywords=[]))
        return ast.copy_location(expression,node)

def original_check(task,code):
    source_tree=ast.parse(task['original_test'])
    last=source_tree.body[-1]
    if not (isinstance(last,ast.Expr) and isinstance(last.value,ast.Call) and isinstance(last.value.func,ast.Name) and last.value.func.id=='check' and len(last.value.args)==1 and isinstance(last.value.args[0],ast.Name) and last.value.args[0].id==task['entry_point']):
        raise ValueError('Unexpected original test entry invocation')
    tracer=OriginalTrace();events=[];tree=tracer.visit(source_tree);ast.fix_missing_locations(tree)
    def record(index,check,message=None):
        try:
            passed=bool(check());events.append({'assert_id':index,'status':'pass' if passed else 'fail'})
        except BaseException as error:
            events.append({'assert_id':index,'status':'timeout' if isinstance(error,CaseTimeout) else 'exception','error_type':type(error).__name__});raise
        if not passed:
            if message is not None:raise AssertionError(message())
            raise AssertionError()
    status='pass';error_type=None
    try:
        fn=load_program(code,task['entry_point'])
        namespace={'_record_assertion':record,task['entry_point']:fn}
        random.seed(0);np.random.seed(0)
        with time_limit(10),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            exec(compile(tree,'released-original-tests-traced','exec'),namespace)
    except BaseException as error:
        status='timeout' if isinstance(error,CaseTimeout) else 'fail' if isinstance(error,AssertionError) else 'exception';error_type=type(error).__name__
    reached={event['assert_id'] for event in events}
    return {'status':status,'error_type':error_type,'assertion_events':events,'static_assertions':tracer.assertions,'unreached_assertion_ids':[row['assert_id'] for row in tracer.assertions if row['assert_id'] not in reached],'instrumentation':'Record each encountered assertion; preserve stop-on-first-failure behavior.'}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--task-file',required=True,type=Path)
    parser.add_argument('--variant',required=True,choices=['reference','canonical','buggy'])
    parser.add_argument('--output-dir',required=True,type=Path)
    parser.add_argument('--expected-file',type=Path)
    args=parser.parse_args();assert_isolation()
    import resource
    resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU,(125,125))
    resource.setrlimit(resource.RLIMIT_FSIZE,(64*1024**2,64*1024**2))
    resource.setrlimit(resource.RLIMIT_NOFILE,(128,128))
    random.seed(0);np.random.seed(0)
    task=json.loads(args.task_file.read_text());output=args.output_dir;output.mkdir(parents=True,exist_ok=True)
    expected={}
    if args.expected_file:
        expected={row['case_id']:row for line in args.expected_file.read_text().splitlines() if line.strip() for row in [json.loads(line)]}
    started=time.monotonic();deadline=started+120
    original=None
    if args.variant!='reference':original=original_check(task,task['programs'][args.variant])
    function=None;load_error=None
    try:function=load_program(task['programs'][args.variant],task['entry_point'])
    except BaseException as error:load_error=type(error).__name__
    random.seed(0);np.random.seed(0)
    counts={};case_path=output/'cases.jsonl'
    with case_path.open('w',encoding='utf-8') as handle:
        for index,case in enumerate(task['cases']):
            row={'task_id':task['task_id'],'variant':args.variant,'case_index':index,'case_id':case['case_id'],'split':case['split'],'memberships':case['memberships']}
            ref=expected.get(case['case_id'])
            if time.monotonic()>=deadline:row['status']='not_run_task_budget'
            elif load_error:row.update(status='program_load_error',error_type=load_error)
            elif args.variant!='reference' and (not ref or ref['status']!='pass'):row['status']='reference_unavailable'
            else:
                limit=5.0 if args.variant=='reference' else min(5.0,max(0.2,4*ref['elapsed_seconds']))
                before=time.monotonic()
                try:
                    with time_limit(min(limit,max(0.001,deadline-before))),warnings.catch_warnings(),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                        warnings.simplefilter('ignore')
                        actual=function(*copy.deepcopy(case['input']))
                        if args.variant=='reference':
                            row.update(status='pass',expected=encode_value(actual))
                        else:
                            row['status']='pass' if compare_output(task['entry_point'],case['input'],actual,decode_value(ref['expected']),task['atol']) else 'fail'
                except BaseException as error:row.update(status='timeout' if isinstance(error,CaseTimeout) else 'exception',error_type=type(error).__name__)
                row['elapsed_seconds']=time.monotonic()-before;row['time_limit_seconds']=limit
            counts[row['status']]=counts.get(row['status'],0)+1
            handle.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n');handle.flush()
    summary={'task_id':task['task_id'],'variant':args.variant,'assigned_cases':len(task['cases']),'status_counts':counts,'original':original,'elapsed_seconds':time.monotonic()-started,'code_sha256':hashlib.sha256(task['programs'][args.variant].encode()).hexdigest(),'isolation_checked':True}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')

if __name__=='__main__':main()
