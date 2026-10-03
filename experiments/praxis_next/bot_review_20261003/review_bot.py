"""Deterministic reviewer. No answer-key access, network calls or language model."""
import math,re
PATTERN=re.compile(r'^(\d+) of 3 members warn\. Mean aggregation (warns|is silent)\. OR aggregation (warns|is silent)\.$')
def parse(text):
    match=PATTERN.fullmatch(text or '')
    if not match:return None
    n,mean,orr=match.groups()
    return {'count':int(n),'mean':mean=='warns','OR':orr=='warns'}
def calculate(vectors):
    if not isinstance(vectors,list) or len(vectors)!=3 or any(v is None for v in vectors):return None
    k=len(vectors[0])
    if k<2 or any(len(v)!=k or any(not isinstance(x,(int,float)) or not math.isfinite(x) or x<0 or x>1 for x in v) or abs(sum(v)-1)>1e-5 for v in vectors):return None
    choices=[max(range(k),key=lambda j:v[j]) for v in vectors]
    averages=[sum(v[j] for v in vectors)/3 for j in range(k)]
    count=sum(j!=0 for j in choices);mean=max(range(k),key=lambda j:averages[j])!=0
    return {'count':count,'mean':mean,'OR':count>0,'answer':count>0 and not mean}
def review(case,bot):
    claims=parse(case.get('explanation'));facts=calculate(case.get('member_probabilities'))
    if bot=='follower':
        if claims is None:return {'status':'ABSTAIN','answer':None}
        return {'status':'FOLLOWED','answer':claims['OR'] and not claims['mean']}
    if facts is None:return {'status':'ABSTAIN','answer':None}
    if bot=='calculator' or case.get('explanation') is None:return {'status':'CALCULATED','answer':facts['answer']}
    if claims is None:return {'status':'REJECTED','answer':None,'numeric_answer':facts['answer'],'reason':'Unsupported explanation format'}
    mismatches=[k for k in ['count','mean','OR'] if facts[k]!=claims[k]]
    if mismatches:return {'status':'REJECTED','answer':None,'numeric_answer':facts['answer'],'reason':'Contradictory claims: '+', '.join(mismatches)}
    return {'status':'VERIFIED','answer':facts['answer']}
