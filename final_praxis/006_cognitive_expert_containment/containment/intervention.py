"""Reversible output hooks for the pinned top-1 MiCRo block architecture."""
import hashlib
import torch

def disagreement(observed_update, alternative_update):
    a=observed_update.float();b=alternative_update.float()
    na=a.norm(dim=-1);nb=b.norm(dim=-1)
    denominator=na*nb
    cosine=(a*b).sum(-1)/denominator.clamp_min(1e-12)
    return torch.where(denominator>1e-12,1-cosine.clamp(-1,1),torch.zeros_like(cosine))

class Containment:
    """No gold, clean reference activation, or corruption identity enters gate()."""
    def __init__(self,model):
        if any(module.training for module in model.modules()):raise ValueError("Evaluation mode required before installing hooks")
        self.model=model;self.handles=[];self.cache={}
        for layer_index,layer in enumerate(model.layers):
            if layer.top_k!=1 or len(layer.experts)!=4 or not getattr(layer,"use_router",False):raise ValueError("Only qualified top-1 four-expert MiCRo")
            self.handles.append(layer.register_forward_pre_hook(self.pre(layer_index),with_kwargs=True))
            for expert_index,expert in enumerate(layer.experts):
                self.handles.append(expert.register_forward_hook(self.capture(layer_index,expert_index)))
            self.handles.append(layer.register_forward_hook(self.post(layer_index)))
        self.configure("none","clean",2.0,0.0,"unset")

    def configure(self,policy,corruption,threshold,random_rate,key):
        if policy not in ("none","conditional","random","permanent","always"):raise ValueError(policy)
        if corruption not in ("clean","negate","permute"):raise ValueError(corruption)
        self.policy=policy;self.corruption=corruption;self.threshold=threshold
        self.random_rate=random_rate;self.key=key
        self.stats={"eligible":0,"interventions":0,"corrupted_selected":0,"distance_sum":0.0,
                    "effective_counts":[0,0,0,0]}
    def pre(self,index):
        def callback(module,args,kwargs):
            if kwargs.get("use_cache") or kwargs.get("past_key_value") is not None:
                raise ValueError("This qualification only supports full-sequence use_cache=False")
            h=args[0] if args else kwargs["hidden_states"]
            if h.shape[1]<=1:raise ValueError("All-expert capture requires sequence length >1")
            self.cache[index]={"h":h,"experts":{}}
        return callback
    def capture(self,index,expert):
        def callback(module,args,output):
            self.cache[index]["experts"][expert]=output[0] if isinstance(output,tuple) else output
        return callback
    def gate(self,observed_update,alternative_update,eligible,index):
        distance=disagreement(observed_update,alternative_update)
        if self.policy=="conditional": chosen=eligible & (distance>self.threshold)
        elif self.policy=="always":chosen=eligible
        elif self.policy=="random":
            seed=int(hashlib.sha256(f"006-random-v1:{self.key}:{index}".encode()).hexdigest()[:16],16)%(2**63)
            generator=torch.Generator(device="cpu").manual_seed(seed)
            uniform=torch.rand(eligible.shape,generator=generator).to(eligible.device)
            chosen=eligible & (uniform<self.random_rate)
        else:chosen=torch.zeros_like(eligible)
        return chosen,distance
    def post(self,index):
        def callback(module,args,output):
            state=self.cache.pop(index);h=state["h"];experts=state["experts"]
            if set(experts)!={0,1,2,3}:raise ValueError("Not all counterfactual expert outputs captured")
            original,router_logits=output
            # This is the pinned decoder-layer return, before model-level reporting transforms.
            probabilities=torch.nn.functional.softmax(router_logits,dim=-1,dtype=torch.float)
            selected=torch.topk(probabilities,1,dim=-1).indices.squeeze(-1)
            eligible=selected.eq(1)
            backup_logits=router_logits.clone();backup_logits[...,1]=-torch.inf
            backup_probabilities=torch.nn.functional.softmax(backup_logits,dim=-1,dtype=torch.float)
            backup=torch.topk(backup_probabilities,1,dim=-1).indices.squeeze(-1)
            stacked=torch.stack([experts[e] for e in range(4)],dim=-2)
            alternative=stacked.gather(-2,backup[...,None,None].expand(*backup.shape,1,h.shape[-1])).squeeze(-2)
            social=experts[1];update=social-h
            # Experimental actuator; only observed output is passed to the gate below.
            if self.corruption=="negate":observed=h-update
            elif self.corruption=="permute":observed=h+torch.roll(update,shifts=17,dims=-1)
            else:observed=social
            replace,distance=self.gate(observed-h,alternative-h,eligible,index)
            if not torch.isfinite(distance[eligible]).all():raise ValueError("Nonfinite gate distance")
            probability=probabilities.max(-1).values
            weight=(probability/(probability+1e-9)).to(h.dtype)
            altered=original+torch.where(eligible[...,None],(observed-social)*weight[...,None],torch.zeros_like(original))
            backup_probability=backup_probabilities.max(-1).values
            backup_weight=(backup_probability/(backup_probability+1e-9)).to(h.dtype)
            result=torch.where(replace[...,None],alternative*backup_weight[...,None],altered)
            if not torch.isfinite(result).all():raise ValueError("Intervention produced nonfinite output")
            effective=torch.where(replace,backup,selected)
            self.stats["eligible"]+=int(eligible.sum())
            self.stats["interventions"]+=int(replace.sum())
            self.stats["corrupted_selected"]+=int(eligible.sum()) if self.corruption!="clean" else 0
            self.stats["distance_sum"]+=float(distance[eligible].sum())
            for e in range(4):self.stats["effective_counts"][e]+=int(effective.eq(e).sum())
            return result,router_logits
        return callback
    def close(self):
        for handle in self.handles:handle.remove()
        self.handles=[];self.cache={}



