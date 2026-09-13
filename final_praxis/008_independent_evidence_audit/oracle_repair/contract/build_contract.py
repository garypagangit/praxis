"""Freeze source-only task contracts. Offline; never reads saved model answers.

Usage: python build_contract.py --audit-cache PATH --private-controls PATH
The first path is the artifact_audit directory; second is PRIVATE_RAW_CLEAN_CONTROLS.json.
Only metadata and reviewer-authored semantic summaries are published.
"""
import argparse
import ast
import collections
import csv
import datetime
import hashlib
import json
import math
from pathlib import Path

SEMANTICS = {
1:'Maximum page count, cast to integer.',2:'Arithmetic mean page count, truncated toward zero.',
3:'Unique nonnull event labels.',4:'Row count with exactly uppercase dinner event.',5:'Row count with exactly uppercase luncheon event.',
6:'Unique nonnull venue labels.',7:'Row count whose occasion lowercases to daily.',8:'Unique nonnull occasion labels; missing values dropped.',
9:'Maximum dish-count divided by page-count ratio.',10:'Mean numeric dish count, truncated toward zero.',11:'Maximum numeric dish-count/page-count ratio; no menu identifier returned.',
12:'Unique location labels among rows with page count above eight; missing labels retained.',13:'Unique nonnull sponsors among dollar-currency rows.',
14:'Sponsors tied for greatest total dish count across their rows.',15:'Unique sponsors among breakfast-event rows.',16:'Unique sponsors among lunch-event rows.',17:'Unique sponsors among dinner-event rows.',
18:'Sponsors with at least two nonnull event records; event distinctness is not required.',19:'Mapping from venue to mean numeric page count.',20:'Unique nonnull sponsor labels.',
21:'Count of event labels equal to banquet after lowercasing.',22:'Distinct nonnull occasion count.',23:'Three venue labels ranked by descending mean numeric dish count.',
24:'Unique nonnull status labels.',25:'Unique nonnull lowercase currency labels.',26:'Year-to-menu-count mapping after datetime parsing.',
27:'Count of complete date/count records dated before 1950; no ratio comparison.',28:'Unique nonnull venues among rows with page count above ten.',29:'Unique lowercase occasion labels containing daily; no menu identities returned.',
30:'Unique nonempty lowercase currency labels.',31:'Distinct nonnull risk-label count.',32:'Percentage of inspection rows with out-of-business result.',
33:'One facility type with maximal record frequency.',34:'All facility types tied for minimal record frequency.',35:'Distinct normalized inspection-type count; missing values become string labels.',
36:'Inspection IDs for failing records of the specified convenience-store brand, preserving record multiplicity.',37:'One business name ranked first by inspection pass proportion; per-business rates omitted.',
38:'Unique facility-type labels of low-risk records.',39:'Unique facility-type labels of high-risk records.',40:'Literal pandas column-oriented JSON text mapping facility types to one modal risk label each.',
41:'Unique known facility-type labels from risk-one records.',42:'Count of grocery-store records with risk-one labels.',43:'Literal pandas column-oriented JSON text mapping facility types to one modal result each.',
44:'Fraction of rows with pass result.',45:'Mean number of nonnull inspection IDs per nonnull facility type.',46:'Risk-label frequency mapping; no level-label relationship calculation.',
47:'One facility type with maximal failed-record fraction.',48:'One business name with most nonnull inspection IDs.',49:'School records with risk-one label and pass result.',
50:'Inspection-record count whose normalized type contains complaint.',51:'Unique facility-type labels from records whose result contains pass.',52:'Nonmissing addresses from low-risk passing records, retaining record multiplicity.',
53:'Unique nonnull result labels from risk-one records.',54:'Maximum parsed inspection year.',55:'All business names tied for maximum record frequency.',56:'Unique license identifiers from passing records.',
57:'Unique business names from risk-three records; no variation over time.',58:'All modal risk labels among restaurant records.',59:'Unique business names on latest parsed inspection date.',
60:'Unique nonnull facility-type labels on latest parsed date; not IDs.',62:'Mean loan amount.',63:'Maximum loan amount.',64:'Minimum loan amount.',
65:'Unique NAICS identifiers on records reporting more than three jobs.',66:'Pearson correlation of loan amount and reported jobs.',67:'Loan-record count in the specified city after lowercasing.',
68:'Up to ten business types ranked by descending loan-record count.',69:'One business type maximizing summed loan amount; amount omitted.',70:'One business type minimizing summed loan amount; amount omitted.',
71:'Yes/no according to whether a ZIP group varies in business type or lender; company identity untested.',72:'Literal pandas column-oriented JSON text with loan-record count by ZIP.',
73:'Literal pandas column-oriented JSON text with summed loan amount by ZIP.',74:'Ordered pair: gender with greatest loan count, gender with greatest loan sum; unanswered category omitted.',
75:'Ordered pair: gender with least loan count, gender with least loan sum; unanswered category retained.',76:'One city maximizing loan sum; amount omitted.',77:'One city minimizing loan sum; amount omitted.',
78:'Literal ZIP string maximizing loan sum; amount omitted.',79:'Literal ZIP string minimizing loan sum; amount omitted.',80:'One race category maximizing loan sum after unanswered category exclusion; amount omitted.',
81:'One race category minimizing loan sum; amount omitted.',87:'Literal pandas column-oriented JSON text mapping cities to loan-sum/job-sum ratio.',89:'Ordered city and ZIP-string pair maximizing loan sum.',
92:'Mean times-appeared count per dish record.',93:'Dish-name records tied for shortest parsed date duration in whole days.',94:'Dish-name records tied for longest parsed date duration.',
98:'Dish-name records tied for minimum positive lowest-price value.',99:'Dish-name records tied for maximum positive lowest-price value.',100:'Earliest dish-name records among pre-2000 first appearances; other pre-2000 records omitted.',
101:'Dish-name records tied for earliest parsed first appearance.',102:'Dish-name records maximizing menu appearance count.',103:'Dish-name records minimizing menu appearance count.',
104:'Parallel ranked arrays of names and maximum prices for ten most frequent dishes; no temporal price series.',105:'Parallel arrays of names and minimum prices for ten least frequent dishes; no greater-than-twenty filter.',
106:'One dish name with minimum finite maximum-price minus minimum-price.',107:'One dish name with maximum maximum-price minus minimum-price.',108:'One dish name with greatest midpoint of price extremes; no specified-dish comparison.',
109:'Five dish-name records ranked by descending times-appeared count.',110:'Literal pandas column-oriented JSON text for ten most frequent dishes and price-extrema midpoint; no temporal change.',
111:'Unique scheduled departure timestamps on late departures; no average delay.',112:'Mean scheduled arrival-minus-departure duration in minutes.',113:'One source label minimizing average departure delay; on-time counts omitted.',
114:'Unique source labels; occurrence counts omitted.',115:'Unique flight labels; frequency ranking omitted.',116:'Scheduled arrival timestamp records with hours 18 through 23; count omitted.',
117:'Unique sources with exactly equal scheduled/actual arrival strings; earlier arrivals and counts omitted.',118:'Unique scheduled departure hour strings on late departures, lexicographically sorted.',
119:'Scheduled arrival timestamp records with hours zero through eleven; count omitted.',120:'Unique sources with late departures; arrival criterion and maximal count omitted.',
121:'Actual departure timestamp records from early departures; flight identities omitted.',122:'Mapping actual-arrival timestamp to actual-departure timestamp for negative durations; duplicate keys overwrite.',
123:'Mapping scheduled-departure hour to mean signed departure delay, including early departures.',124:'Sorted unique scheduled hour strings among exactly equal arrival strings; frequency maximum omitted.',
125:'Unique source labels on records with parseable departure times; monthly/on-time conditions omitted.',126:'Unique scheduled arrival timestamps among exactly equal arrival strings; inequality count omitted.',
127:'Distinct nonnull city count.',128:'Unique city labels including missing values.',129:'Unique county labels including missing values.',130:'County-to-count mapping for top three counts of acute-care emergency-service hospitals.',
131:'City-to-distinct-owner-count mapping; ZIP restriction and ownership modes omitted.',132:'Distinct lowercase hospital-type count; name-length calculation omitted.',133:'Count of acute-care hospital records offering emergency services.',
134:'Ordered hospital-type/ownership pair of one maximal-frequency combination.',135:'Number of county/emergency groups; per-group hospital counts omitted.',136:'Distinct cities with private voluntary-nonprofit hospitals offering emergency services.',
137:'Number of counties with a nonnull group key; hospital-type mapping omitted.',138:'Unique cities with government-owned acute-care hospitals; critical-access and dominance criteria absent.',
139:'ZIP-to-sum-of-type-and-owner-distinct-counts mapping; not a count of ZIPs.',140:'Top-three city shares among all acute-care records; city total-hospital denominator absent.',
141:'City-to-unique-hospital-type mapping; ZIP and evolution absent.',142:'One hospital type with most emergency-service records; trends/rates omitted.',143:'Distinct lowercase hospital-type count; owner/county comparison absent.',
144:'Distinct lowercase emergency-service label count; ownership association absent.',145:'Count of cities with at least one emergency-service record; size correlation absent.',146:'Hospital-type-to-distinct-ZIP-count mapping.',
147:'Distinct lowercase hospital-type count; ownership correlation absent.',148:'Distinct county labels among emergency-service records, including missing labels.',149:'Distinct types among government-owned hospitals; multi-type ZIP filter and hospital identities absent.',
150:'Distinct hospital-type labels among emergency-service records, including missing labels.',151:'Unique cities with private voluntary-nonprofit hospital records; hospitals/types omitted.',
152:'Unique cities with any government-owned hospital; dominance not tested.',153:'Unique nonnull ZIP identifiers among emergency-service hospitals; density association absent.',154:'Unique nonnull hospital ownership labels; three-owner city restriction and hospitals absent.'
}

# Reviewed against authoritative purpose rows, executable queries, clean/raw controls.
# Exclusions are frozen without viewing model outcomes; omitted IDs are provisional,
# not certified, semantic matches subject to the limitations in CONTRACT.md.
ISSUES = {
2:('invalid','UNSPECIFIED_TRUNCATION','Mean truncated to integer without a rounding instruction.'),
3:('invalid','COUNT_LIST_MISMATCH','Distinct labels returned where a count is requested.'),
6:('invalid','COUNT_LIST_MISMATCH','Distinct venues returned where a count is requested.'),
8:('invalid','COUNT_LIST_AND_NULL_MISMATCH','Count requested with explicit missing-label replacement; list returned after dropping nulls.'),
10:('invalid','UNSPECIFIED_TRUNCATION','Mean truncated to integer without a rounding instruction.'),
11:('invalid','ENTITY_VALUE_MISMATCH','Numeric ratio returned instead of the requested menu identity.'),
12:('invalid','COUNT_LIST_AND_NULL_MISMATCH','Location count and missing-location replacement not implemented.'),
14:('ambiguous','AGGREGATION_SCOPE','Purpose can mean a single menu maximum; query sums dishes over sponsor records.'),
16:('ambiguous','COMPOUND_EVENT_SCOPE','Clean data contain compound lunch event labels omitted by exact-event equality; offering versus category identity is unresolved.'),
17:('ambiguous','COMPOUND_EVENT_SCOPE','Clean data contain compound dinner event labels omitted by exact-event equality; offering versus category identity is unresolved.'),
18:('ambiguous','EVENT_DISTINCTNESS','Two event records can be duplicates; distinct event availability is not established.'),
20:('invalid','COUNT_LIST_MISMATCH','Sponsor labels returned instead of count.'),
24:('invalid','COUNT_LIST_MISMATCH','Status labels returned instead of requested number of statuses.'),
27:('invalid','WRONG_STATISTIC','Pre-1950 record count does not test later-year ratio differences.'),
29:('invalid','ENTITY_VALUE_MISMATCH','Occasion strings returned instead of filtered menus.'),
30:('invalid','COUNT_LIST_MISMATCH','Currency labels returned instead of count.'),
32:('ambiguous','UNIT_OF_ANALYSIS','Purpose refers to businesses; query counts inspection rows without business deduplication.'),
33:('ambiguous','UNDEFINED_MAIN_TYPES','Plural main types has no cardinality definition; only one modal label is returned.'),
37:('invalid','REQUIRED_VALUES_OMITTED','Requested per-brand pass rates and ranking are reduced to one brand name.'),
38:('ambiguous','FACILITY_TYPE_VS_ENTITY','Purpose can request facility entities; query returns facility-type labels.'),
39:('ambiguous','FACILITY_TYPE_VS_ENTITY','Purpose can request facility entities; query returns facility-type labels.'),
40:('ambiguous','MODAL_TIE_AND_SERIALIZATION','Clean-table modal risk ties are reduced to one label; literal JSON comparison imposes incidental serialization.'),
42:('ambiguous','STORE_VS_INSPECTION_UNIT','Query counts inspection rows, while distinct store entities can have repeated records.'),
43:('ambiguous','FACILITY_TYPE_VS_ENTITY','Each facility is grouped by facility type rather than business identity.'),
46:('invalid','WRONG_STATISTIC','Frequency of whole risk strings is not the requested level-label relationship.'),
48:('ambiguous','TIED_ENTITY_REPRESENTATION','Clean-table maximum inspection frequency has multiple tied business names; only one is returned.'),
49:('invalid','RISK_DIRECTION','Safety/lowest risk requested; query selects Risk 1, which source risk labels identify as high.'),
51:('ambiguous','FACILITY_TYPE_VS_ENTITY','Locate facilities is reduced to facility-type labels.'),
52:('ambiguous','ADDRESS_ENTITY_MULTIPLICITY','Returned address records can repeat across inspections; facility versus record multiplicity is unspecified.'),
53:('ambiguous','CONTRADICTORY_RISK_LABEL','Purpose names Risk 1 as low although source labels use Risk 1 high; query ignores the contradiction.'),
57:('invalid','TEMPORAL_TEST_OMITTED','No within-business risk variation or time analysis.'),
60:('ambiguous','IDENTIFIER_MISMATCH','Purpose asks for an ID of facility type; no type-ID field or mapping is supplied.'),
68:('ambiguous','RANK_TIES','Equal-frequency business types have arbitrary relative order under ordered-list diagnostic.'),
69:('invalid','REQUIRED_VALUES_OMITTED','Requested dollar amounts omitted.'),70:('invalid','REQUIRED_VALUES_OMITTED','Requested dollar amounts omitted.'),
71:('invalid','WRONG_IDENTITY_PROXY','Variation in business type or lender does not establish distinct company identity.'),
72:('ambiguous','UNSPECIFIED_TARGET','Purpose asks for a given ZIP but supplies none; query returns all ZIPs.'),
73:('ambiguous','UNSPECIFIED_TARGET','Purpose asks for a given ZIP but supplies none; query returns all ZIPs.'),
74:('ambiguous','UNSPECIFIED_EXCLUSION','Query excludes unanswered gender although purpose gives no exclusion; requested amount may also require numeric values.'),
75:('ambiguous','UNCLEAR_PURPOSE','Districts, gender categories and requested numeric values are not resolved by task wording.'),
76:('invalid','REQUIRED_VALUES_OMITTED','Requested dollar amounts omitted.'),77:('invalid','REQUIRED_VALUES_OMITTED','Requested dollar amounts omitted.'),
78:('invalid','REQUIRED_VALUES_OMITTED','Requested dollar amounts omitted.'),79:('invalid','REQUIRED_VALUES_OMITTED','Requested dollar amounts omitted.'),
80:('invalid','REQUIRED_VALUES_OMITTED','Dollar amounts omitted and unanswered race excluded without instruction.'),81:('invalid','REQUIRED_VALUES_OMITTED','Requested dollar amounts omitted.'),
87:('ambiguous','SEMANTIC_JSON_CONTRACT_UNRESOLVED','Literal column-oriented JSON comparison can reject mathematically equivalent city-ratio mappings.'),
93:('ambiguous','NAME_ENTITY_MULTIPLICITY','Clean shortest-duration output contains repeated names; required name versus record multiplicity is unresolved.'),
94:('ambiguous','NAME_ENTITY_MULTIPLICITY','Dish names are returned with record multiplicity; entity/name-set semantics are not established.'),
98:('ambiguous','UNSPECIFIED_EXCLUSION','Query discards zero/nonpositive prices; purpose gives no such rule.'),99:('ambiguous','UNSPECIFIED_EXCLUSION','Query discards zero/nonpositive prices; purpose gives no such rule.'),
100:('invalid','EXTRA_EXTREMUM_FILTER','Only earliest names returned instead of all pre-2000 names.'),
101:('ambiguous','NAME_ENTITY_MULTIPLICITY','Dish names are returned with record multiplicity; entity/name-set semantics are not established.'),
102:('ambiguous','NAME_ENTITY_MULTIPLICITY','Dish names are returned with record multiplicity; entity/name-set semantics are not established.'),
103:('ambiguous','NAME_ENTITY_MULTIPLICITY','Dish names are returned with record multiplicity; entity/name-set semantics are not established.'),
104:('invalid','TEMPORAL_TEST_AND_NONFINITE','Static maxima cannot establish evolution; released reference contains NaN.'),
105:('invalid','WRONG_FILTER_AND_RANKING','Ten least frequent rows replace the requested greater-than-twenty condition.'),
106:('ambiguous','TIED_ENTITY_REPRESENTATION','Plural dish request reduced to one idxmin result; tie coverage unspecified.'),
107:('ambiguous','TIED_ENTITY_REPRESENTATION','Plural dish request reduced to one idxmax result; tie coverage unspecified.'),
108:('invalid','WRONG_STATISTIC','Maximum midpoint dish name does not compare average price of a given dish.'),
109:('ambiguous','RANK_TIES','Top-five clean-table frequencies include a tie; ordered-list diagnostic imposes arbitrary tie order.'),
110:('invalid','TEMPORAL_TEST_OMITTED','Static midpoint of extremes is not average-price change.'),
111:('invalid','WRONG_STATISTIC','Late-departure timestamp list instead of average departure delay.'),
113:('invalid','WRONG_STATISTIC','Minimal mean-delay carrier instead of requested performance/on-time counts.'),
114:('invalid','COUNT_LIST_MISMATCH','Unique sources instead of carrier occurrence counts.'),
115:('invalid','FREQUENCY_TEST_OMITTED','All flight labels instead of modal flight.'),
116:('invalid','COUNT_LIST_MISMATCH','Timestamp records instead of count; hour 18 inclusion also differs from strictly after 18:00.'),
117:('invalid','WRONG_COMPARATOR_AND_STATISTIC','Equality omits early arrivals; sources replace grouped counts.'),
118:('invalid','WRONG_DIRECTION_AND_OUTPUT','Query selects actual departure later than scheduled and emits hours, not requested classification.'),
119:('invalid','WRONG_INTERVAL_AND_OUTPUT','Query includes midnight through 05:59 and emits records rather than count.'),
120:('invalid','WRONG_TIME_FIELD_AND_STATISTIC','Departure lateness replaces arrival criterion; no maximum-count selection.'),
121:('ambiguous','TIMESTAMP_VS_FLIGHT_ID','Timestamps may not identify flights; no task decision on duplicate timestamps.'),
122:('ambiguous','LOSSY_RECORD_MAPPING','Timestamp-keyed mapping can overwrite distinct flights sharing an arrival timestamp.'),
123:('ambiguous','DELAY_POPULATION','Query averages all signed departure differences, whereas delayed-only trend is also a plausible reading.'),
124:('invalid','FREQUENCY_TEST_OMITTED','All exactly-on-time hours instead of maximum-frequency hour.'),
125:('invalid','TEMPORAL_TEST_OMITTED','Neither month nor on-time departure condition is applied.'),
126:('invalid','WRONG_COMPARATOR_AND_OUTPUT','Equal-arrival timestamp labels replace unequal-arrival count.'),
128:('invalid','COUNT_LIST_MISMATCH','City labels instead of count.'),129:('invalid','COUNT_LIST_MISMATCH','County labels instead of count.'),
130:('ambiguous','TOP_K_BOUNDARY_TIE','Four counties tie for the maximum count in the clean table; query chooses three without a purpose tie policy.'),
131:('invalid','WRONG_STATISTIC','Distinct-owner count per city replaces ownership modes restricted to multi-ZIP cities.'),
132:('invalid','WRONG_STATISTIC','Hospital-type count replaces grouped average name lengths.'),
133:('ambiguous','HOSPITAL_VS_RECORD_UNIT','Clean query counts nineteen qualifying rows but only fifteen distinct provider identifiers; purpose asks hospital count.'),
134:('ambiguous','TIED_ENTITY_REPRESENTATION','Plural combinations reduced to one maximal pair; tie policy absent.'),
135:('invalid','GROUP_COUNT_MISMATCH','Number of groups instead of hospital counts within groups.'),
136:('ambiguous','OWNERSHIP_SUBTYPE_RESTRICTION','Broad voluntary nonprofits reduced to private voluntary nonprofits without a task restriction.'),
137:('invalid','GROUP_COUNT_MISMATCH','County count instead of county/type mapping.'),
138:('invalid','WRONG_TYPE_AND_DOMINANCE','Acute care replaces critical access, and any presence replaces dominance.'),
139:('ambiguous','UNDEFINED_DIVERSITY','Sum of marginal distinct counts is only one possible diversity measure and does not count ZIPs.'),
140:('invalid','WRONG_DENOMINATOR','Acute-care share across cities replaces acute/total within each city.'),
141:('invalid','WRONG_GROUPING','City type sets omit ZIP variation and evolution.'),
142:('invalid','WRONG_STATISTIC','One maximum count type replaces trends across high-count types.'),
143:('invalid','WRONG_STATISTIC','Type count replaces owner/county comparison.'),144:('invalid','WRONG_STATISTIC','Service-label count replaces ownership/service association.'),
145:('invalid','WRONG_STATISTIC','Any-service city count replaces size/service correlation.'),
146:('ambiguous','DISTRIBUTION_COLLAPSE','Only distinct ZIP count per type remains; geography itself is omitted.'),
147:('invalid','WRONG_STATISTIC','Type count replaces ownership/type correlation.'),
149:('invalid','WRONG_FILTER_AND_OUTPUT','Multi-type ZIP criterion and hospital identities omitted.'),
151:('invalid','REQUIRED_VALUES_OMITTED','City labels omit requested hospital entities and hospital types.'),
152:('invalid','DOMINANCE_TEST_OMITTED','Any government presence does not establish dominance.'),
153:('invalid','WRONG_STATISTIC','ZIP list does not establish density/service association.'),
154:('invalid','WRONG_FILTER_AND_OUTPUT','Ownership label list omits three-owner-city predicate and hospital entities.')
}

ORDERED = {23,68,74,75,89,109,134}
MULTISET = {36,52,93,94,98,99,100,101,102,103,116,119,121}
IDENTIFIERS = {36,56,65,78,79,89,153}
FLOATS = {9,11,19,32,44,45,62,63,64,66,92,112,123,140}
ENCODED_JSON = {40,43,72,73,87,110}

def digest(b): return hashlib.sha256(b).hexdigest()
def canonical(x): return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=True).encode('utf-8')
def nonfinite(x):
    if isinstance(x,float): return not math.isfinite(x)
    if isinstance(x,list): return any(map(nonfinite,x))
    if isinstance(x,dict): return any(map(nonfinite,x.values()))
    return False

def mapping(i):
    if i<31:return 'menu',f'datasets/menu_datasets/menu_p{i}.csv',f'datasets/menu_datasets/clean_tables/menu_sample_p{i}.csv'
    if i<62:return 'chi',f'datasets/CFI_datasets/chi_food_data_p{i}.csv',f'datasets/CFI_datasets/cleaned_tables/chi_sample_p{i}.csv'
    if i<92:return 'ppp',f'datasets/ppp_datasets/ppp_data_p{i}.csv',f'datasets/ppp_datasets/cleaned_tables/ppp_sample_p{i}.csv'
    if i<111:return 'dish',f'datasets/dish_datasets/dish_data_p{i}.csv',f'datasets/dish_datasets/cleaned_tables/dish_sample_p{i}.csv'
    if i<127:return 'flights',f'datasets/flights/flights_data_p{i}.csv',f'datasets/flights/cleaned_tables/flights_data_p{i}.csv'
    return 'hos',f'datasets/hospital/hos_data_p{i}.csv',f'datasets/hospital/clean_tables/hos_pp{i}.csv'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--audit-cache',type=Path,required=True);ap.add_argument('--private-controls',type=Path,required=True);args=ap.parse_args()
    cache=args.audit_cache/'inventory/cache';source=args.audit_cache/'source'
    qpath=source/'evaluation/q_execution.py';qb=qpath.read_bytes();qt=qb.decode('utf-8');tree=ast.parse(qt)
    klass=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='QExecute')
    funcs={int(n.name[2:-4]):n for n in klass.body if isinstance(n,ast.FunctionDef)}
    purpose_path='purposes/all_purposes.csv';rows=list(csv.DictReader((cache/purpose_path).open(encoding='utf-8-sig')))
    gold_path='CoT.rerun/answer_1-154_gt.json';gold_lines=(source/gold_path).read_text(encoding='utf-8').splitlines()
    gold={r['pp_id']:(line_no,r,line) for line_no,line in enumerate(gold_lines,1) for r in [json.loads(line)]}
    controls={r['id']:r for r in json.loads(args.private_controls.read_text(encoding='utf-8'))}
    entries=[]
    for row_number,r in enumerate(rows,2):
        i=int(r['ID']);domain,raw,clean=mapping(i);gline,grecord,gtext=gold[i];answer=grecord['answer'];f=funcs[i]
        assert i in SEMANTICS and r['Purposes']==grecord['purpose']
        typ=type(answer).__name__;mode='ordered' if i in ORDERED else 'multiset' if i in MULTISET else 'set' if typ=='list' else 'ordered'
        spec={'numeric_mode':'tolerant' if i in FLOATS else 'exact','abs_tol':1e-8 if i in FLOATS else 0,'rel_tol':1e-9 if i in FLOATS else 0,'list_mode':mode}
        if i in {104,105}:spec['columnar_mode']='ordered'
        if i==141:spec['list_mode']='set'
        status,code,reason=ISSUES.get(i,('eligible_provisional','NO_IDENTIFIED_SEMANTIC_CONFLICT','Purpose and observable agree under the disclosed query conventions; not independent certification.'))
        obs=controls[i]['clean']['answer']
        # This is a source-control check, never a model-output score.
        comparison='unresolved_nonfinite_reference' if nonfinite(answer) else 'equal' if obs==answer else 'permutation_only' if isinstance(obs,list) and collections.Counter(map(repr,obs))==collections.Counter(map(repr,answer)) else 'mismatch'
        e={'id':i,'domain':domain,'source_table_group':domain,'purpose':{'path':purpose_path,'csv_row_number':row_number,'row_sha256':digest(canonical(r)),'text_sha256':digest(r['Purposes'].encode('utf-8'))},
           'query':{'path':'evaluation/q_execution.py','function':f.name,'start_line':f.lineno,'end_line':f.end_lineno,'function_sha256':digest(ast.get_source_segment(qt,f).encode('utf-8')),'observable':SEMANTICS[i]},
           'reference':{'path':gold_path,'jsonl_line':gline,'record_sha256':digest(gtext.encode('utf-8')),'answer_type':typ,'contains_nonfinite':nonfinite(answer)},
           'tables':{kind:{'path':p,'sha256':digest((cache/p).read_bytes()),'rows':controls[i][kind]['rows'],'columns':len(controls[i][kind]['columns'])} for kind,p in [('raw',raw),('clean',clean)]},
           'scorer_spec':spec,'value_role':'identifier' if i in IDENTIFIERS else 'literal_encoded_json' if i in ENCODED_JSON else 'numeric_statistic' if typ in {'int','float'} else 'task_labels_or_mapping',
           'purpose_status':status,'purpose_valid_eligible':status=='eligible_provisional','purpose_eligible':status=='eligible_provisional','issue_code':code,'issue_reason':reason,
           'upstream_diagnostic_eligible':not nonfinite(answer),'clean_query_reference_control':comparison,
           'null_and_failure_contract':'Nonfinite reference invalidates this diagnostic denominator; prediction null/nonfinite, swallowed-error sentinels and exceptions remain failures unless an independently valid empty result is established. Upstream defaults are recorded, not reinterpreted as missing-label replacement.'}
        entries.append(e)
    assert len(entries)==142 and set(SEMANTICS)=={e['id'] for e in entries}
    doc={'schema_version':1,'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'upstream_repository':'https://github.com/LanLi2017/LLM4DC','upstream_revision':'082dcbf5304329ef1ff08f5830e4116256b00a59',
         'scope':'Source/query/reference-only freeze before repaired model-output scoring; no corrected gold or model calls.',
         'source_files':[{'path':p,'sha256':digest((base/p).read_bytes())} for base,p in [(cache,purpose_path),(source,'evaluation/q_execution.py'),(source,gold_path)]],
         'counts':dict(collections.Counter(e['purpose_status'] for e in entries)),
         'controls':dict(collections.Counter(e['clean_query_reference_control'] for e in entries)),
         'raw_clean_private_control_sha256':digest(args.private_controls.read_bytes()),
         'tasks':entries}
    out=Path(__file__).parent/'TASK_CONTRACTS.json';out.write_text(json.dumps(doc,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'manifest':str(out),'sha256':digest(out.read_bytes()),'counts':doc['counts'],'controls':doc['controls']}))

if __name__=='__main__':main()
