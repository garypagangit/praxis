"""Uncapped full-release sensitivity analysis, separated by source sensor."""
import pathlib,json,csv,hashlib,datetime,time,collections,gc,array
import numpy as np
from lightgbm import LGBMClassifier
from sklearn.metrics import confusion_matrix,precision_recall_fscore_support,roc_auc_score,average_precision_score
import joblib
ROOT=pathlib.Path(__file__).resolve().parent
PRIVATE=pathlib.Path('C:/w/praxis_full_release_20260927');PRIVATE.mkdir(exist_ok=True)
INV=pathlib.Path('C:/w/apt_benchmark_20260920/experiments/apt_benchmark/host_history_exfil/DATA_INVENTORY.json')
STAGES={'Benign':0,'Reconnaissance':1,'Establish Foothold':1,'Cover up':1,'Lateral Movement':2,'Data Exfiltration':3}
CLASSES=['Benign','OtherAttackStage','MovementAuthorLabel','ExfiltrationAuthorLabel']
PARAMS=dict(n_estimators=300,num_leaves=15,learning_rate=.05,min_child_samples=10,reg_lambda=1.,random_state=20260927,n_jobs=6,deterministic=True,force_col_wise=True,verbosity=-1)
CAL=datetime.datetime(2021,6,27,tzinfo=datetime.timezone.utc).timestamp()*1000
TEST=datetime.datetime(2021,6,28,tzinfo=datetime.timezone.utc).timestamp()*1000
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
def write(p,d):p.parent.mkdir(exist_ok=True,parents=True);p.write_text(json.dumps(d,indent=2,allow_nan=False),encoding='utf-8')
def role(ip):
 p=ip.split('.')
 return {'1':1,'2':1,'3':1,'4':2,'5':3}.get(p[2],0) if len(p)==4 and p[:2]==['10','1'] else 0
def metrics(y,p):
 pred=p.argmax(1);pr,re,fs,su=precision_recall_fscore_support(y,pred,labels=range(4),zero_division=0)
 return {'rows':len(y),'macro_f1':float(fs.mean()),'confusion':confusion_matrix(y,pred,labels=range(4)).tolist(),'benign_false_alerts':int(((y==0)&(pred!=0)).sum()),'benign_fpr':float((pred[y==0]!=0).mean()) if (y==0).any() else None,'classes':{name:{'support':int(su[k]),'precision':float(pr[k]),'recall':float(re[k]) if su[k] else None,'f1':float(fs[k]) if su[k] else None,'warning_recall':float((pred[y==k]!=0).mean()) if su[k] and k else None,'missed_warnings':int(((y==k)&(pred==0)).sum()) if k else None,'roc_auc':float(roc_auc_score(y==k,p[:,k])) if 0<su[k]<len(y) else None,'average_precision':float(average_precision_score(y==k,p[:,k])) if su[k] else None} for k,name in enumerate(CLASSES)}}
def prepare(sensor,files,raw):
 out=PRIVATE/sensor;out.mkdir(exist_ok=True);path=out/'DATA.npz'
 if path.exists():return np.load(path,allow_pickle=False),json.loads((out/'PREPARATION.json').read_text())
 receipt=[];xs=array.array('f');ys=array.array('b');starts=array.array('d');ends=array.array('d');roles=array.array('b');caps=array.array('h');ids=bytearray();rowids=array.array('i')
 excluded={'id','expiration_id','src_ip','dst_ip','src_mac','dst_mac','src_oui','dst_oui','src_port','dst_port','vlan_id','tunnel_id'}
 for ci,item in enumerate(files):
  p=raw/item['source_file'];assert sha(p)==item['sha256'],str(p)
  counts=collections.Counter();count=0
  with p.open(encoding='utf-8-sig',newline='') as f:
   reader=csv.reader(f);header=next(reader);pos={n:i for i,n in enumerate(header)}
   names=[n for n in header[:77] if n not in excluded and 'first_seen' not in n and 'last_seen' not in n];ix=[pos[n] for n in names]
   for rn,row in enumerate(reader,2):
    stage=row[-3];assert len(row)>=89 and stage in STAGES,(item['source_file'],rn,stage)
    nums=[float(row[i]) for i in ix];src=row[pos['src_ip']];dst=row[pos['dst_ip']];sport=int(row[pos['src_port']]);dport=int(row[pos['dst_port']]);start=float(row[pos['bidirectional_first_seen_ms']]);end=float(row[pos['bidirectional_last_seen_ms']])
    assert np.isfinite(nums).all() and 0<start<=end
    nums.extend([float(dport in {22,135,139,445,3389,5985,5986}),float(dport in {80,443,8080,8443}),float(dport==53)])
    key=hashlib.sha256(json.dumps([src,dst,sport,dport,start,end,*nums],separators=(',',':')).encode()).digest()
    xs.extend(nums);ys.append(STAGES[stage]);starts.append(start);ends.append(end);roles.extend((role(src),role(dst)));caps.append(ci);ids.extend(key);rowids.append(rn);counts[stage]+=1;count+=1
  assert count==item['rows'] and dict(counts)==item['right_anchored_stage_counts']
  receipt.append({'source_file':item['source_file'],'sha256':item['sha256'],'rows':count,'native_counts':dict(counts)});print(sensor,'read',ci+1,'/',len(files),'rows',len(ys),flush=True)
 X=np.frombuffer(xs,dtype=np.float32).reshape(len(ys),-1);y=np.frombuffer(ys,dtype=np.int8);start=np.frombuffer(starts,dtype=np.float64);end=np.frombuffer(ends,dtype=np.float64);r=np.frombuffer(roles,dtype=np.int8).reshape(-1,2);cap=np.frombuffer(caps,dtype=np.int16);keys=np.frombuffer(ids,dtype='S32');rn=np.frombuffer(rowids,dtype=np.int32)
 # Same observable identity within a sensor is counted once; conflicting labels quarantine all copies.
 _,first,inv,counts=np.unique(keys,return_index=True,return_inverse=True,return_counts=True)
 lo=np.full(len(first),4,dtype=np.int8);hi=np.full(len(first),-1,dtype=np.int8);np.minimum.at(lo,inv,y);np.maximum.at(hi,inv,y)
 conflict=lo!=hi;keep=first[~conflict];duplicates=int(np.sum(counts[~conflict]-1));conflicts=int(counts[conflict].sum())
 X,y,start,end,r,cap,keys,rn=[v[keep] for v in [X,y,start,end,r,cap,keys,rn]]
 split=np.full(len(y),-1,np.int8);split[end<CAL]=0;split[(start>=CAL)&(end<TEST)]=1;split[start>=TEST]=2
 R=np.column_stack([np.eye(4,dtype=np.float32)[r[:,0]],np.eye(4,dtype=np.float32)[r[:,1]]])
 np.savez_compressed(path,X=X,R=R,y=y,start=start,end=end,split=split,capture=cap,keys=keys,source_row=rn)
 prep={'sensor':sensor,'raw_rows':sum(x['rows'] for x in receipt),'retained_rows':len(y),'exact_duplicate_rows_removed':duplicates,'conflicting_rows_quarantined':conflicts,'boundary_overlap_rows_excluded':int((split<0).sum()),'files':receipt,'features':names+['dst_remote_admin_service','dst_web_service','dst_dns_service'],'split_counts':{name:np.bincount(y[split==k],minlength=4).tolist() for k,name in [(0,'train'),(1,'calibration'),(2,'test')]},'data_sha256':sha(path)}
 write(out/'PREPARATION.json',prep);write(ROOT/'evidence'/sensor/'PREPARATION.json',prep);gc.collect();return np.load(path,allow_pickle=False),prep
def main():
 inv=json.loads(INV.read_text());files=inv['files'];groups=collections.defaultdict(list)
 for f in files:groups[pathlib.Path(f['source_file']).name.split('_')[0]].append(f)
 plan={'status':'FROZEN_BEFORE_NEW_FULL_RELEASE_FITS','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'inventory_sha256':sha(INV),'source_commit':inv['source_commit'],'files':len(files),'raw_rows_expected':sum(x['rows'] for x in files),'sensors':sorted(groups),'classes':CLASSES,'native_mapping':STAGES,'calibration_start_utc':'2021-06-27T00:00:00Z','test_start_utc':'2021-06-28T00:00:00Z','boundary_policy':'Exclude flows crossing a cutoff; train completion precedes calibration start; calibration completion precedes test start.','training':'Every eligible training row, no class cap, no resampling, no class weighting.','arms':['current','current_roles'],'model_parameters':PARAMS,'decision':'Multiclass argmax; align probability columns to fixed schema.','role_features':'Eight coarse topology indicators; other does not mean Internet.','selection_rule':'On calibration choose highest macro-F1, ties current. Conservative review permits roles only if macro-F1 increases, each supported attack-stage warning recall is no more than 0.01 below current, and benign FPR no more than 0.001 above current. Unsupported attack classes make review provisional. Evaluate fixed choices on test without retuning.','analysis':'Report all sensor views individually; no pooled independent-sensor confidence interval. One deterministic fit per arm; original seed sensitivity remains.','scope':'Full released flow-table coverage. Same exposed campaign and dependent sensors, not independent replication. This extends population/training coverage for a roles comparison, not a rerun of every historical acquisition intervention. No new history, future-feature or source-sensor identity inputs.'}
 freeze=ROOT/'FULL_RELEASE_PROTOCOL.json'
 if not freeze.exists():write(freeze,plan)
 else:plan=json.loads(freeze.read_text());assert plan['inventory_sha256']==sha(INV)
 results=[]
 for sensor in sorted(groups):
  dest=ROOT/'evidence'/sensor/'RESULTS.json'
  if dest.exists():results.append(json.loads(dest.read_text()));continue
  fs=sorted(groups[sensor],key=lambda x:(x['minimum_first_seen_ms'],x['source_file']));data,prep=prepare(sensor,fs,pathlib.Path(inv['private_raw_root']));y=data['y'];split=data['split'];a=split==0;b=split==1;c=split==2
  assert data['end'][a].max()<data['start'][b].min() and data['end'][b].max()<data['start'][c].min()
  arms={};starttime=time.time()
  for arm in ['current','current_roles']:
   X=data['X'] if arm=='current' else np.column_stack([data['X'],data['R']]);model=LGBMClassifier(**PARAMS);t=time.time();model.fit(X[a],y[a]);print('FIT',sensor,arm,'train',int(a.sum()),'seconds',round(time.time()-t,2),flush=True)
   outputs={}
   for name,mask in [('calibration',b),('test',c)]:
    p=np.zeros((int(mask.sum()),4),dtype=np.float64)
    if len(model.classes_)==1:p[:,int(model.classes_[0])]=1.0
    else:p[:,model.classes_]=model.predict_proba(X[mask])
    outputs[name]=metrics(y[mask],p);outputs[name]['training_classes']=model.classes_.tolist();outputs[name]['single_class_training']=len(model.classes_)==1
    np.savez_compressed(PRIVATE/sensor/(arm+'_'+name+'.npz'),y=y[mask],p=p,keys=data['keys'][mask],capture=data['capture'][mask])
    if name=='test':outputs['per_capture']={fs[int(ci)]['source_file']:metrics(y[mask][data['capture'][mask]==ci],p[data['capture'][mask]==ci]) for ci in np.unique(data['capture'][mask])}
   joblib.dump(model,PRIVATE/sensor/(arm+'.joblib'));arms[arm]=outputs;del X;gc.collect()
  cm=arms['current']['calibration'];rm=arms['current_roles']['calibration'];f1choice='current_roles' if rm['macro_f1']>cm['macro_f1'] else 'current'
  supported=[n for n in CLASSES[1:] if cm['classes'][n]['support']]
  allowed=rm['macro_f1']>cm['macro_f1'] and all(rm['classes'][n]['warning_recall']>=cm['classes'][n]['warning_recall']-.01 for n in supported) and rm['benign_fpr']<=cm['benign_fpr']+.001
  reviewchoice='current_roles' if allowed else 'current'
  result={'sensor':sensor,'preparation':prep,'arms':arms,'calibration_selection':{'f1_choice':f1choice,'review_choice':reviewchoice,'review_provisional_missing_classes':[n for n in CLASSES[1:] if n not in supported],'f1_selected_test':arms[f1choice]['test'],'review_selected_test':arms[reviewchoice]['test']},'seconds':time.time()-starttime,'protocol_sha256':sha(freeze)}
  write(dest,result);results.append(result);data.close();gc.collect();print('COMPLETE',sensor,flush=True)
 write(ROOT/'FULL_RELEASE_RESULTS.json',{'protocol_sha256':sha(freeze),'sensors':results,'raw_rows':sum(x['preparation']['raw_rows'] for x in results),'model_fits':2*len(results),'complete_source_file_coverage':sum(len(x['preparation']['files']) for x in results)==len(files),'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
if __name__=='__main__':main()
