"""Read only the command sheet; retain private commands outside Git."""
from pathlib import Path
import collections,datetime,hashlib,json,re,zipfile
import xml.etree.ElementTree as E

HERE=Path(__file__).resolve().parent
SOURCE=next(Path('C:/Users/garyp/Downloads').glob('GAMBiT*Command Logs.xlsx'))
PRIVATE=Path('C:/w/aivh_review_20261005/gambit');PRIVATE.mkdir(exist_ok=True)
NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile(SOURCE) as z:
    strings=[''.join(x.itertext()) for x in E.fromstring(z.read('xl/sharedStrings.xml'))]
    root=E.fromstring(z.read('xl/worksheets/sheet4.xml'))
    rows=[]
    for row in root.findall('.//m:sheetData/m:row',NS):
        values={}
        for c in row:
            v=c.find('m:v',NS);text=v.text if v is not None else ''
            if c.get('t')=='s':text=strings[int(text)]
            elif c.get('t')=='inlineStr':text=''.join(c.itertext())
            values[re.sub(r'\d','',c.get('r'))]=text
        rows.append(values)
assert [rows[0].get(k) for k in 'ABCD']==['Timestamp','Command','PID','MITRE Technique']
records=[dict(zip(['timestamp','command','participant','technique'],[r.get(k,'') for k in 'ABCD'])) for r in rows[1:]]
nonempty=[r for r in records if any(r.values())]
groups=collections.Counter(r['participant'] for r in nonempty if r['participant'])
techniques=collections.Counter(r['technique'] for r in nonempty if r['technique'])
bad_dates=0; dates=[];backward=0;last={};per_day=collections.Counter()
for r in nonempty:
    try:t=datetime.datetime.fromisoformat(r['timestamp'].replace('Z','+00:00'))
    except (ValueError,TypeError):bad_dates+=1;continue
    dates.append(t.isoformat());per_day[(r['participant'],t.date().isoformat())]+=1
    if r['participant'] in last and t<last[r['participant']]:backward+=1
    last[r['participant']]=t
dup=len(nonempty)-len(set(tuple(r.values()) for r in nonempty))
attributable=[r for r in nonempty if re.fullmatch(r'E\d{2}P\d+',r['participant']) and r['command'].strip() not in ('','NA')]
unique=list({tuple(r.values()):r for r in attributable}.values())
qualified=[];out_of_period=0
for r in unique:
    try:t=datetime.datetime.fromisoformat(r['timestamp'].replace('Z','+00:00'))
    except (ValueError,TypeError):continue
    if t.year not in (2024,2025):out_of_period+=1;continue
    qualified.append(r)
report={'status':'ACQUIRED_STRUCTURAL_QUALIFICATION_ONLY','source_bytes':SOURCE.stat().st_size,
        'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'sheet':'Exp 1+2 Commands & MITRE Techni','data_rows':len(records),'nonempty_rows':len(nonempty),
        'missing_fields':{k:sum(not r[k].strip() for r in nonempty) for k in records[0]},
        'participant_ids':len(groups),'rows_per_participant':dict(sorted(groups.items())),
        'participant_prefix_rows':dict(collections.Counter(r['participant'].split('P')[0] for r in nonempty)),
        'distinct_technique_strings':len(techniques),'technique_counts':dict(techniques),
        'duplicate_exact_rows':dup,'invalid_timestamps':bad_dates,'backward_steps_in_sheet_per_participant':backward,
        'timestamp_min':min(dates) if dates else None,'timestamp_max':max(dates) if dates else None,
        'participant_days':len(per_day),'participants_with_at_least_ten_rows':sum(v>=10 for v in groups.values()),
        'placeholder_merged_rows':sum(r['participant']=='merged' and r['command']=='NA' for r in nonempty),
        'attributable_command_rows':len(attributable),
        'attributable_participant_ids':len(set(r['participant'] for r in attributable)),
        'attributable_exact_duplicates':len(attributable)-len(unique),
        'unique_out_of_collection_year_rows':out_of_period,
        'structurally_eligible_unique_rows':len(qualified),
        'eligible_participant_ids':len(set(r['participant'] for r in qualified)),
        'pending':['Verify AI-assistance rules for strict human-only labels',
                   'Verify experiment/control mapping; do not infer from worksheet title alone',
                   'Determine whether curated commands omit unannotated/failed actions',
                   'Resolve participant identity across experiments before grouping',
                   'Qualify shared behavior/observation window against agent logs'],
        'raw_workbook_committed':False,'demographic_and_psychometric_values_used':False,
        'model_fit_or_scoring_performed':False}
(PRIVATE/'commands.json').write_text(json.dumps(nonempty,ensure_ascii=False),encoding='utf-8')
(PRIVATE/'commands_structurally_eligible.json').write_text(json.dumps(qualified,ensure_ascii=False),encoding='utf-8')
(HERE/'GAMBIT_QUALIFICATION.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['rows_per_participant','technique_counts']},indent=2))
