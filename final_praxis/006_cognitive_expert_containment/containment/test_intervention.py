import unittest
import torch
from intervention import Containment,disagreement

class Expert(torch.nn.Module):
    def __init__(self,index):super().__init__();self.index=index
    def forward(self,hidden_states):
        update=(self.index+1)+torch.arange(hidden_states.shape[-1],dtype=hidden_states.dtype)*.001
        return (hidden_states+update,)

class Block(torch.nn.Module):
    top_k=1;use_router=True
    def __init__(self):
        super().__init__();self.experts=torch.nn.ModuleList([Expert(i) for i in range(4)]);self.router_values=[0.,2.,1.,-1.]
    def forward(self,hidden_states,ablate=None,use_cache=False,past_key_value=None):
        logits=torch.tensor(self.router_values).expand(*hidden_states.shape[:-1],4).clone()
        if "social" in (ablate or []):logits[...,1]=-torch.inf
        probabilities=logits.softmax(-1);selected=probabilities.topk(1,-1).indices.squeeze(-1)
        values=torch.stack([expert(hidden_states)[0] for expert in self.experts],dim=-2)
        selected_values=values.gather(-2,selected[...,None,None].expand(*selected.shape,1,hidden_states.shape[-1])).squeeze(-2)
        p=probabilities.max(-1).values
        return selected_values*(p/(p+1e-9))[...,None],logits

class Model(torch.nn.Module):
    def __init__(self):super().__init__();self.layers=torch.nn.ModuleList([Block()])
    def forward(self,h,ablate=None):
        return self.layers[0](h,ablate=ablate or [],use_cache=False)[0]

class Tests(unittest.TestCase):
    def test_sham_and_remove_hooks(self):
        model=Model().eval();h=torch.zeros(1,3,32);original=model(h)
        hooks=Containment(model)
        hooks.configure("none","clean",2,0,"q")
        self.assertTrue(torch.equal(original,model(h)))
        hooks.close();self.assertTrue(torch.equal(original,model(h)))

    def test_negation_preserves_update_norm(self):
        model=Model().eval();h=torch.zeros(1,3,32);original=model(h)
        hooks=Containment(model);hooks.configure("none","negate",2,0,"q")
        corrupted=model(h)
        self.assertTrue(torch.equal(original,-corrupted))
        self.assertTrue(torch.equal((original-h).norm(dim=-1),(corrupted-h).norm(dim=-1)))
        self.assertEqual(hooks.stats["corrupted_selected"],3)
        hooks.close()

    def test_conditional_recovers_backup_and_matches_permanent(self):
        model=Model().eval();h=torch.zeros(1,3,32);permanent=model(h,["social"])
        hooks=Containment(model);hooks.configure("conditional","negate",1,0,"q")
        conditional=model(h)
        self.assertTrue(torch.allclose(conditional,permanent,atol=1e-6))
        self.assertEqual(hooks.stats["interventions"],3)
        hooks.configure("conditional","clean",1,0,"q");model(h)
        self.assertEqual(hooks.stats["interventions"],0)
        hooks.close()

    def test_gate_ignores_corruption_flag_given_same_observation(self):
        model=Model().eval();hooks=Containment(model);observed=torch.ones(1,3,32)
        backup=-observed;eligible=torch.ones(1,3,dtype=torch.bool)
        hooks.configure("conditional","clean",1,0,"q");first=hooks.gate(observed,backup,eligible,0)
        hooks.configure("conditional","negate",1,0,"q");second=hooks.gate(observed,backup,eligible,0)
        self.assertTrue(torch.equal(first[0],second[0]));self.assertTrue(torch.equal(first[1],second[1]))
        self.assertTrue(torch.equal(disagreement(observed,torch.zeros_like(observed)),torch.zeros(1,3)))
        hooks.close()
    def test_only_actually_selected_positions_are_corrupted(self):
        model=Model().eval();h=torch.zeros(1,3,32)
        model.layers[0].router_values=[[0.,2.,1.,-1.],[2.,0.,1.,-1.],[0.,1.,2.,-1.]]
        baseline=model(h);hooks=Containment(model);hooks.configure("none","negate",2,0,"q")
        changed=model(h)
        self.assertTrue(torch.equal(changed[:,0],-baseline[:,0]))
        self.assertTrue(torch.equal(changed[:,1:],baseline[:,1:]))
        self.assertEqual(hooks.stats["eligible"],1)
        hooks.configure("none","clean",2,0,"q")
        self.assertTrue(torch.equal(model(h),baseline));hooks.close()

    def test_float32_probability_tie_matches_upstream_selection(self):
        model=Model().eval();h=torch.zeros(1,3,32)
        model.layers[0].router_values=[0.,1e-8,0.,0.]
        baseline=model(h)
        actual=int(torch.tensor(model.layers[0].router_values).softmax(-1).topk(1).indices[0])
        hooks=Containment(model);hooks.configure("none","negate",2,0,"q")
        changed=model(h)
        self.assertTrue(torch.equal(changed,-baseline if actual==1 else baseline))
        self.assertEqual(hooks.stats["eligible"],3 if actual==1 else 0);hooks.close()

if __name__=="__main__":unittest.main()


