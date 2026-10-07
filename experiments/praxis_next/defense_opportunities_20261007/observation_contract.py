"""Research decision aid for declared log availability; never classifies an operator."""
import argparse,json,pathlib
HERE=pathlib.Path(__file__).resolve().parent
def assess(view,unknown_possible=True):
 summary=json.loads((HERE/'evidence/SUMMARY.json').read_text());rows=json.loads((HERE/'evidence/RESULTS.json').read_text())
 hit=next((r for r in summary['logging'] if r['view']==view),None)
 if hit is None:return {'decision':'unmeasured_view','deployment_certified':False,'view':view}
 relevant=[r for r in rows if r['study']=='logging' and r['model']=='lexical' and r['setting'].endswith('/'+view+('/full' if view=='full' else '/adapted'))]
 errors=[r['selective']['accepted_error'] for r in relevant if r['selective']['accepted_error'] is not None]
 return {'decision':'research_only','deployment_certified':False,'view':view,'logging_80pct_f1_gate':hit['passes'],'worst_environment_f1':hit['adapted_min'],'largest_observed_selective_error':max(errors) if errors else None,'unknown_possible':unknown_possible,'unknown_early_gate_passed_all_settings':any(r['passed']==r['settings'] for r in summary['unknown_policies']),'requirements':['Same declared observation view at training and use','Independent version/environment qualification','Validated unknown-family handling before attribution','Qualified timestamps and independently reviewed extraction for timing/typos'],'scope':'Measured synthetic views of this Honey cohort only; F1 is not a per-session confidence probability. Observing a supported view alone cannot certify identity.'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--view',required=True);p.add_argument('--closed-world-assumption',action='store_true');a=p.parse_args();print(json.dumps(assess(a.view,not a.closed_world_assumption),indent=2))
