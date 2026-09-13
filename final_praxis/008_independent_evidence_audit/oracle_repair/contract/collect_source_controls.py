"""Reproduce private raw/clean query controls, offline and without model outputs.

The output contains source-derived answers. Keep it outside the publication tree.
"""
import argparse
import ast
import contextlib
import csv
import io
import json
import re
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
from build_contract import mapping

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--audit-cache',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    if args.output.resolve().is_relative_to(Path(__file__).parent.resolve()):
        raise SystemExit('Private source-derived answers must be written outside the contract publication directory.')
    source=(args.audit_cache/'source/evaluation/q_execution.py').read_text(encoding='utf-8');tree=ast.parse(source)
    allowed=[n for n in tree.body if (isinstance(n,ast.ClassDef) and n.name=='QExecute') or (isinstance(n,ast.FunctionDef) and n.name=='safe_parse_datetime') or (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ISO_8601_REGEX' for t in n.targets))]
    ns={'pd':pd,'np':np,'re':re};exec(compile(ast.Module(body=allowed,type_ignores=[]),'reviewed-query-functions','exec'),ns)
    rows=list(csv.DictReader((args.audit_cache/'inventory/cache/purposes/all_purposes.csv').open(encoding='utf-8-sig')))
    controls=[]
    for r in rows:
        i=int(r['ID']);domain,raw,clean=mapping(i);rec={'id':i,'domain':domain}
        for kind,p in [('raw',raw),('clean',clean)]:
            df=pd.read_csv(args.audit_cache/'inventory/cache'/p);f=getattr(ns['QExecute'],f'pp{i}_exe');buf=io.StringIO()
            try:
                with warnings.catch_warnings(record=True) as ws,contextlib.redirect_stdout(buf):
                    warnings.simplefilter('always');answer=f(df.copy(deep=True))
                answer=json.loads(json.dumps(answer,default=lambda x:x.item() if hasattr(x,'item') else str(x)))
                rec[kind]={'answer':answer,'error':None,'warnings':len(ws),'rows':len(df),'columns':list(df.columns)}
            except Exception as e:
                rec[kind]={'answer':None,'error':type(e).__name__+':'+str(e),'rows':len(df),'columns':list(df.columns)}
        controls.append(rec)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(controls,indent=2,allow_nan=True),encoding='utf-8')
    print(json.dumps({'tasks':len(controls),'query_executions':2*len(controls),'private_output':str(args.output)}))

if __name__=='__main__':main()
