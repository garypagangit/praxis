"""Read-only pinned artifact inventory. Standard library only; never imports upstream code.

Run: python inventory.py [--refresh]
Writes receipts/cache only beside this script. HTTP GETs only to GitHub API/raw.
"""
import collections
import concurrent.futures
import csv
import hashlib
import io
import json
import math
import pathlib
import re
import sys
import urllib.parse
import urllib.request

COMMIT = '082dcbf5304329ef1ff08f5830e4116256b00a59'
REPO = 'LanLi2017/LLM4DC'
HERE = pathlib.Path(__file__).resolve().parent
REFRESH = '--refresh' in sys.argv

def sha(b):
    return hashlib.sha256(b).hexdigest()

def get_url(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'LLM4DC-read-only-artifact-inventory'}), timeout=45) as r:
        return r.read()

tree_url = f'https://api.github.com/repos/{REPO}/git/trees/{COMMIT}?recursive=1'
tree_path = HERE / 'tree.json'
if REFRESH or not tree_path.exists():
    tree_path.write_bytes(get_url(tree_url))
tree_bytes = tree_path.read_bytes()
tree = json.loads(tree_bytes)
assert tree['sha'] == COMMIT and tree['truncated'] is False
blobs = {x['path']: x for x in tree['tree'] if x['type'] == 'blob'}

def fetch(path):
    target = HERE / 'cache' / path
    url = f'https://raw.githubusercontent.com/{REPO}/{COMMIT}/' + urllib.parse.quote(path)
    if REFRESH or not target.exists():
        b = get_url(url)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b)
    b = target.read_bytes()
    actual = hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest()
    assert actual == blobs[path]['sha'], (path, actual, blobs[path]['sha'])
    assert len(b) == blobs[path]['size']
    return path, b, {'path': path, 'url': url, 'size': len(b), 'sha256': sha(b), 'git_blob_sha1': actual}

purpose_paths = ['purposes/all_purposes.csv', 'purposes/all_purposes_full.csv', 'dataset-all - all_purposes.csv']
purpose_bytes = {p: fetch(p)[1] for p in purpose_paths}
purpose_tables = {p: list(csv.DictReader(io.StringIO(b.decode('utf-8-sig')))) for p, b in purpose_bytes.items()}
rows = purpose_tables[purpose_paths[0]]
ids = {int(r['ID']) for r in rows}
assert len(ids) == len(rows) == 142

def mapping(i):
    if i < 31: return 'menu', f'datasets/menu_datasets/menu_p{i}.csv', f'datasets/menu_datasets/clean_tables/menu_sample_p{i}.csv'
    if i < 62: return 'chi', f'datasets/CFI_datasets/chi_food_data_p{i}.csv', f'datasets/CFI_datasets/cleaned_tables/chi_sample_p{i}.csv'
    if i < 92: return 'ppp', f'datasets/ppp_datasets/ppp_data_p{i}.csv', f'datasets/ppp_datasets/cleaned_tables/ppp_sample_p{i}.csv'
    if i < 111: return 'dish', f'datasets/dish_datasets/dish_data_p{i}.csv', f'datasets/dish_datasets/cleaned_tables/dish_sample_p{i}.csv'
    if i < 127: return 'flights', f'datasets/flights/flights_data_p{i}.csv', f'datasets/flights/cleaned_tables/flights_data_p{i}.csv'
    return 'hos', f'datasets/hospital/hos_data_p{i}.csv', f'datasets/hospital/clean_tables/hos_pp{i}.csv'

pairs = [{'id': i, 'domain': mapping(i)[0], 'raw': mapping(i)[1], 'clean': mapping(i)[2]} for i in sorted(ids)]
missing = [dict(id=p['id'], kind=k, path=p[k]) for p in pairs for k in ('raw', 'clean') if p[k] not in blobs]
answer_paths = sorted(p for p in blobs if '/answer_' in p and p.endswith('.json'))
paths = sorted(set(purpose_paths + answer_paths + ['evaluation/q_execution.py', 'evaluation/answer_analysis.py', 'dcw_evaluate.py'] + [p[k] for p in pairs for k in ('raw', 'clean') if p[k] in blobs]))
data, receipts = {}, []
with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
    for p, b, receipt in pool.map(fetch, paths):
        data[p] = b
        receipts.append(receipt)

def csv_info(b):
    rr = list(csv.reader(io.StringIO(b.decode('utf-8-sig'))))
    return {'rows': len(rr)-1, 'columns': rr[0], 'malformed_row_numbers': [i+2 for i, r in enumerate(rr[1:]) if len(r) != len(rr[0])]}

pair_issues = []
for p in pairs:
    if p['raw'] in data and p['clean'] in data:
        p['raw_csv'] = csv_info(data[p['raw']])
        p['clean_csv'] = csv_info(data[p['clean']])
        p['identical_bytes'] = data[p['raw']] == data[p['clean']]
        p['column_order_equal'] = p['raw_csv']['columns'] == p['clean_csv']['columns']
        p['row_count_equal'] = p['raw_csv']['rows'] == p['clean_csv']['rows']
        if not p['column_order_equal'] or not p['row_count_equal'] or p['raw_csv']['malformed_row_numbers'] or p['clean_csv']['malformed_row_numbers']:
            pair_issues.append(p['id'])

def nonfinite(x):
    if isinstance(x, float): return int(not math.isfinite(x))
    if isinstance(x, list): return sum(nonfinite(v) for v in x)
    if isinstance(x, dict): return sum(nonfinite(v) for v in x.values())
    return 0

def nonfinite_paths(x, path='answer'):
    if isinstance(x, float) and not math.isfinite(x): return [path]
    if isinstance(x, list): return [p for i,v in enumerate(x) for p in nonfinite_paths(v,f'{path}[{i}]')]
    if isinstance(x, dict): return [p for k,v in x.items() for p in nonfinite_paths(v,f'{path}[{k!r}]')]
    return []

answers = {}
parsed = {}
purposes = {int(r['ID']): r['Purposes'] for r in rows}
for p in answer_paths:
    b = data[p]
    try:
        json.loads(b)
        whole_json = True
    except json.JSONDecodeError:
        whole_json = False
    a = [json.loads(line) for line in b.decode('utf-8-sig').splitlines() if line.strip()]
    parsed[p] = a
    counts = collections.Counter(r['pp_id'] for r in a)
    answers[p] = {'rows': len(a), 'unique_ids': len(counts), 'duplicate_ids': sorted(k for k,v in counts.items() if v>1), 'missing_purpose_ids': sorted(ids-set(counts)), 'extra_ids': sorted(set(counts)-ids), 'whole_file_valid_json': whole_json, 'format': 'JSON' if whole_json else 'JSONL', 'answer_types': dict(collections.Counter(type(r.get('answer')).__name__ for r in a)), 'nonfinite_values': sum(nonfinite(r.get('answer')) for r in a), 'null_answer_ids': [r['pp_id'] for r in a if r.get('answer') is None], 'empty_answer_ids': [r['pp_id'] for r in a if r.get('answer') in ('', [], {})], 'purpose_text_mismatch_ids': [r['pp_id'] for r in a if r.get('purpose') != purposes.get(r['pp_id'])]}
    answers[p]['parser'] = 'Python json.loads per nonempty line; permissive NaN/Infinity accepted, counted, never repaired'
    answers[p]['nonfinite_paths'] = [{'id':r['pp_id'],'paths':nonfinite_paths(r.get('answer'))} for r in a if nonfinite(r.get('answer'))]

gt = {r['pp_id']: r for r in parsed['evaluation/answer_1-154_gt.json']}
for p,a in parsed.items():
    answers[p]['answer_type_mismatch_gt_ids'] = [r['pp_id'] for r in a if r['pp_id'] in gt and type(r.get('answer')) is not type(gt[r['pp_id']]['answer'])]
    answers[p]['literal_answer_equal_gt_count'] = sum(r.get('answer') == gt.get(r['pp_id'],{}).get('answer') for r in a)
    answers[p]['literal_comparison_not_a_score'] = True

groups = collections.defaultdict(list)
for p,x in blobs.items():
    if '/datasets_llm/' in p and p.endswith('.csv'):
        m = re.search(r'_p(\d+)\.csv$',p)
        groups[str(pathlib.PurePosixPath(p).parent)].append({'path':p, 'id': int(m.group(1)) if m else None, 'size':x['size'], 'git_blob_sha1':x['sha']})
saved = {}
for group, entries in sorted(groups.items()):
    present = [e['id'] for e in entries if e['id'] is not None]
    saved[group] = {'files':len(entries), 'unique_ids':len(set(present)), 'missing_purpose_ids':sorted(ids-set(present)), 'extra_ids':sorted(set(present)-ids), 'duplicate_ids':sorted(k for k,v in collections.Counter(present).items() if v>1), 'files_and_git_hashes':entries}

purpose_comparison = {}
for p,rr in purpose_tables.items():
    mm = {int(r['ID']):r for r in rr}
    purpose_comparison[p] = {'rows':len(rr), 'missing_purpose_ids':sorted(ids-set(mm)), 'extra_ids':sorted(set(mm)-ids), 'text_mismatch_main_ids':[i for i in sorted(ids&set(mm)) if mm[i]['Purposes'] != purposes[i]]}

semantic_examples = [{'id':i,'purpose':purposes[i],'gt_answer':gt[i]['answer'],'gt_type':type(gt[i]['answer']).__name__} for i in sorted(ids) if isinstance(gt[i]['answer'],(list,dict)) and re.search(r'\b(number of|how many|count)\b', purposes[i], re.I)]
report = {'repository':REPO,'commit':COMMIT,'scope':'No upstream code executed; no model inference. Standard-library CSV/JSON parsing and tree inventory only. Raw/clean shape differences are observations, not necessarily defects. Model CSV files are tree-inventoried, not executed or semantically validated.','script_sha256':sha(pathlib.Path(__file__).read_bytes()),'tree':{'url':tree_url,'sha256':sha(tree_bytes),'blob_count':len(blobs),'truncated':False},'purpose_tables':purpose_comparison,'purpose_ids':sorted(ids),'absent_ids_within_1_154':sorted(set(range(1,155))-ids),'domain_counts':dict(collections.Counter(p['domain'] for p in pairs)),'missing_raw_clean':missing,'raw_clean_pairs':pairs,'raw_clean_shape_difference_or_malformed_ids':pair_issues,'identical_raw_clean_count':sum(p.get('identical_bytes',False) for p in pairs),'saved_answers':answers,'saved_model_csv_groups':saved,'count_wording_nonscalar_gt_examples_heuristic_only':semantic_examples,'gt_copies_identical':data['evaluation/answer_1-154_gt.json']==data['CoT.rerun/answer_1-154_gt.json'],'verified_download_receipts':receipts}
(HERE/'inventory_receipt.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({'purpose_rows':len(rows),'domains':report['domain_counts'],'missing_raw_clean':missing,'shape_difference_ids':pair_issues,'identical_raw_clean':report['identical_raw_clean_count'],'answer_files':len(answers),'model_csv_groups':{g:{k:v for k,v in x.items() if k!='files_and_git_hashes'} for g,x in saved.items()},'purpose_text_mismatches':purpose_comparison,'count_wording_nonscalar_gt_ids':[x['id'] for x in semantic_examples],'gt_types':answers['evaluation/answer_1-154_gt.json']['answer_types'],'receipt_sha256':sha((HERE/'inventory_receipt.json').read_bytes())},indent=2))
