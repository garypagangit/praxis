"""Independent stdlib-only AWS audit; deliberately does not import replay code."""
import hashlib,json,math,multiprocessing as mp,os,platform,sys,time

def audit(records,queue,shard):
    checks=0; calculated=[]
    for cm in records:
        n=sum(map(sum,cm));support=[sum(row) for row in cm]
        den=[support[k]+sum(row[k] for row in cm) for k in range(4)]
        f1=sum(2*cm[k][k]/den[k] if den[k] else 0 for k in range(4))/4
        fa=sum(cm[0][1:]);warnings=sum(sum(row[1:]) for row in cm)
        expected=[f1,fa,fa/support[0],warnings/n*100000]
        for k in [1,2,3]:expected.extend([cm[k][0],1-cm[k][0]/support[k],cm[k][k]/support[k]])
        calculated.append([round(float(v),9) for v in expected])
        checks+=len(expected)
    # Exact rank counting with ties and finite sample correction, independent implementation.
    for scores in [list(range(101)),[0]*20+[1]*30+[8]*20+[10]*31]:
        for alpha in [.01,.02,.05,.1]:
            misses=0
            for j,s in enumerate(scores):
                training=sorted(scores[:j]+scores[j+1:]);rank=math.floor(alpha*(len(training)+1))
                cutoff=training[rank-1] if rank else -math.inf
                misses+=s<cutoff
            assert misses/len(scores)<=alpha+1e-12;checks+=1
    queue.put({'pid':os.getpid(),'shard':shard,'unique_matrices':len(records),'checks':checks,'passed':True,'calculated':calculated})

def main():
    data=json.load(open(sys.argv[1]));ctx=mp.get_context('spawn');q=ctx.Queue();start=time.monotonic()
    ps=[ctx.Process(target=audit,args=(data['records'][i::2],q,i)) for i in range(2)]
    for p in ps:p.start()
    receipts=[q.get(timeout=60) for _ in ps]
    for p in ps:p.join(60);assert p.exitcode==0,p.exitcode
    all_values=[None]*len(data['records'])
    for r in receipts:all_values[r['shard']::2]=r.pop('calculated')
    digest=hashlib.sha256(json.dumps(all_values,separators=(',',':')).encode()).hexdigest()
    assert digest==data['expected_metrics_sha256']
    assert len({r['pid'] for r in receipts})==2
    print(json.dumps({'passed':True,'parallel_workers':2,'receipts':receipts,'represented_result_rows':data['represented_result_rows'],'unique_matrices':len(data['records']),'input_sha256':hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest(),'wall_seconds':time.monotonic()-start,'python':sys.version,'platform':platform.platform(),'scope':'Independent metric and rank-rule audit only. Full scientific replay ran locally.','gpu_used':False}),flush=True)
if __name__=='__main__':main()
