"""Independent synthetic purpose controls; no saved model predictions or reference values.

All tables below are artificial. Expected answers were specified from task semantics
before invoking upstream queries. A negative control PASS confirms a discrepancy,
and does not credit the source query as correct.
"""
import argparse
import ast
import contextlib
import datetime
import hashlib
import io
import json
import re
import warnings
from pathlib import Path
import numpy as np
import pandas as pd

# (task ID, rationale, artificial columns, independently specified expected result,
#  expected relationship). These check observable semantics, not model quality.
CASES=[
(1,'Maximum count',{'page_count':[2,7,3]},7,'equal'),
(2,'Arithmetic mean preserves fractional part',{'page_count':[1,2]},1.5,'different'),
(3,'Distinct-label request is a count',{'event':['a','b','a',None]},2,'different'),
(4,'Exact requested event row count',{'event':['DINNER','DINNER','dinner','x']},2,'equal'),
(6,'Distinct venue count',{'venue':['a','b','a',None]},2,'different'),
(8,'Missing occasion is an explicit unknown category',{'occasion':['a','a',None]},2,'different'),
(10,'Arithmetic mean dish count preserves fractions',{'dish_count':[1,2]},1.5,'different'),
(11,'Requested menu identity differs from maximum ratio',{'id':['m1','m2'],'dish_count':[4,12],'page_count':[2,3]},['m2'],'different'),
(18,'Repeated occurrence is not two distinct available events',{'sponsor':['s','s'],'event':['breakfast','breakfast']},[],'different'),
(19,'Mean count by venue',{'venue':['a','a','b'],'page_count':[1,2,8]},{'a':1.5,'b':8.0},'equal'),
(20,'Distinct sponsor count',{'sponsor':['a','a','b']},2,'different'),
(22,'Distinct occasion count excludes missing',{'occasion':['a','a','b',None]},2,'equal'),
(24,'Distinct status count',{'status':['a','a','b']},2,'different'),
(30,'Distinct currency count',{'currency':['Dollars','dollars','Euros']},2,'different'),
(31,'Distinct risk count',{'Risk':['r1','r1','r2']},2,'equal'),
(34,'All minimal-frequency type ties',{'Facility Type':['a','a','b','c']},['b','c'],'equal_set'),
(44,'Pass fraction',{'Results':['pass','PASS','fail','out of business']},0.5,'equal'),
(45,'Average inspections per facility type',{'Facility Type':['a','a','b'],'Inspection ID':[1,2,3]},1.5,'equal'),
(49,'Safest category follows low risk label, not risk number one',{'Facility Type':['school','school','school'],'Risk':['Risk 1 (High)','Risk 1 (High)','Risk 3 (Low)'],'Results':['pass','pass','pass']},1,'different'),
(50,'Complaint substring count',{'Inspection Type':['Complaint','Complaint Re-Inspection','Routine']},2,'equal'),
(54,'Latest parsed year',{'Inspection Date':['2020-01-01','2022-01-01']},2022,'equal'),
(55,'All modal business names',{'DBA Name':['a','a','b','b','c']},['a','b'],'equal_set'),
(62,'Mean loan amount',{'LoanAmount':[1.0,2.0,6.0]},3.0,'equal'),
(63,'Maximum loan amount',{'LoanAmount':[1.0,2.0,6.0]},6.0,'equal'),
(64,'Minimum loan amount',{'LoanAmount':[1.0,2.0,6.0]},1.0,'equal'),
(65,'Code identities are selected, not averaged',{'JobsReported':[4,3,9],'NAICSCode':['001','002','003']},['001','003'],'equal_set'),
(66,'Perfect positive Pearson correlation',{'LoanAmount':[2.0,4.0,6.0],'JobsReported':[1.0,2.0,3.0]},1.0,'equal_numeric'),
(67,'City comparison is case-insensitive',{'City':['Honolulu','HONOLULU','elsewhere']},2,'equal'),
(68,'Business types ranked by loan count',{'BusinessType':['a','a','a','b','b','c']},['a','b','c'],'equal'),
(93,'Shortest calendar interval',{'name':['a','b'],'first_appeared':['2000-01-01T00:00:00Z','2000-01-01T00:00:00Z'],'last_appeared':['2000-01-02T00:00:00Z','2000-01-05T00:00:00Z']},['a'],'equal'),
(94,'Longest calendar interval',{'name':['a','b'],'first_appeared':['2000-01-01T00:00:00Z','2000-01-01T00:00:00Z'],'last_appeared':['2000-01-02T00:00:00Z','2000-01-05T00:00:00Z']},['b'],'equal'),
(100,'All pre-cutoff names, not only earliest',{'name':['a','b','c'],'first_appeared':['1990-01-01','1995-01-01','2001-01-01'],'last_appeared':['2000-01-01']*3},['a','b'],'different'),
(101,'Earliest dish records',{'name':['a','b'],'first_appeared':['1990-01-01','1995-01-01']},['a'],'equal'),
(102,'Greatest menu appearance count',{'name':['a','b'],'menus_appeared':[4,9]},['b'],'equal'),
(103,'Least menu appearance count',{'name':['a','b'],'menus_appeared':[4,9]},['a'],'equal'),
(111,'Average signed departure delay in minutes',{'sched_dep_time':['2020-01-01T10:00:00Z']*2,'act_dep_time':['2020-01-01T10:10:00Z','2020-01-01T10:20:00Z']},15.0,'different'),
(112,'Average scheduled duration in minutes',{'sched_dep_time':['2020-01-01T10:00:00Z']*2,'sched_arr_time':['2020-01-01T11:00:00Z','2020-01-01T12:00:00Z']},90.0,'equal'),
(115,'Most frequent flight identity',{'flight':['f1','f1','f2']},'f1','different'),
(117,'No-later-than arrivals count includes early flights',{'src':['a','a'],'sched_arr_time':['2020-01-01T10:00:00Z']*2,'act_arr_time':['2020-01-01T09:59:00Z','2020-01-01T10:00:00Z']},{'a':2},'different'),
(119,'Morning interval begins at 06:00 and answer is count',{'sched_arr_time':['2020-01-01T01:00:00Z','2020-01-01T07:00:00Z']},1,'different'),
(126,'Count unequal arrivals',{'sched_arr_time':['2020-01-01T10:00:00Z']*2,'act_arr_time':['2020-01-01T10:00:00Z','2020-01-01T11:00:00Z']},1,'different'),
(127,'Distinct city count',{'City':['a','a','b']},2,'equal'),
(128,'Different city count',{'City':['a','a','b']},2,'different'),
(129,'Different county count',{'CountyName':['a','a','b']},2,'different'),
(132,'Average name length per type and owner',{'HospitalName':['aa','aaaa'],'HospitalType':['acute','acute'],'HospitalOwner':['private','private']},{'acute/private':3.0},'different'),
(133,'Acute-care emergency hospital count',{'HospitalType':['acute care hospitals','acute care hospitals','other'],'EmergencyService':['yes','no','yes']},1,'equal'),
(135,'Counts within county/service groups',{'CountyName':['a','a','b'],'EmergencyService':['yes','yes','no']},{'a/yes':2,'b/no':1},'different'),
(138,'Critical-access criterion differs from acute-care criterion',{'City':['critical_city','acute_city'],'HospitalType':['Critical Access Hospitals','Acute Care Hospitals'],'HospitalOwner':['Government','Government']},['critical_city'],'different'),
(140,'Acute-care fraction uses each city denominator',{'City':['a','a','a','a','b'],'HospitalType':['acute care hospitals','other','other','other','acute care hospitals']},{'b':1.0,'a':0.25},'different'),
(148,'Count counties offering emergency services',{'CountyName':['a','a','b'],'EmergencyService':['yes','yes','no']},1,'equal'),
(150,'Count types offering emergency services',{'HospitalType':['acute','acute','other'],'EmergencyService':['yes','yes','yes']},2,'equal'),
(152,'Any government presence need not dominate',{'City':['a','a','a'],'HospitalOwner':['government','private','private']},[],'different'),
(154,'Hospital filter requires a city with at least three owner types',{'City':['a','a','b'],'HospitalName':['h1','h2','h3'],'HospitalOwner':['government','private','private']},[],'different'),
]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--query-source',type=Path,required=True);args=ap.parse_args()
    source=args.query_source.read_bytes();tree=ast.parse(source.decode('utf-8'))
    allowed=[n for n in tree.body if (isinstance(n,ast.ClassDef) and n.name=='QExecute') or (isinstance(n,ast.FunctionDef) and n.name=='safe_parse_datetime') or (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ISO_8601_REGEX' for t in n.targets))]
    ns={'pd':pd,'np':np,'re':re};exec(compile(ast.Module(body=allowed,type_ignores=[]),'reviewed-upstream-query-functions','exec'),ns)
    results=[]
    for i,rationale,data,expected,relation in CASES:
        with warnings.catch_warnings(record=True),contextlib.redirect_stdout(io.StringIO()):
            got=getattr(ns['QExecute'],f'pp{i}_exe')(pd.DataFrame(data))
        got=json.loads(json.dumps(got,default=lambda x:x.item() if hasattr(x,'item') else str(x)))
        equal=(set(got)==set(expected)) if relation=='equal_set' else abs(got-expected)<1e-10 if relation=='equal_numeric' else got==expected
        passed=not equal if relation=='different' else equal
        results.append({'id':i,'rationale':rationale,'expected_relationship':relation,'passed':bool(passed),'synthetic_data_sha256':hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest(),'expected_answer_sha256':hashlib.sha256(json.dumps(expected,sort_keys=True).encode()).hexdigest(),'observed_answer_sha256':hashlib.sha256(json.dumps(got,sort_keys=True).encode()).hexdigest()})
    report={'schema_version':1,'executed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'query_source_sha256':hashlib.sha256(source).hexdigest(),'case_count':len(results),'passed':sum(r['passed'] for r in results),'purpose_matching_controls':sum(r['expected_relationship']!='different' for r in results),'purpose_discrepancy_controls':sum(r['expected_relationship']=='different' for r in results),'cases':results}
    (Path(__file__).parent/'SEMANTIC_CONTROLS.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='cases'}))
    if report['passed']!=len(results):
        print('Failed IDs:',[r['id'] for r in results if not r['passed']]);raise SystemExit(1)

if __name__=='__main__':main()
