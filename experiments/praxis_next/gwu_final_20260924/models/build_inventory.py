"""Read-only implementation/configuration audit; never fits or predicts."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib
import importlib.metadata
import json
import warnings

import joblib
from lightgbm import LGBMClassifier,LGBMRegressor

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
PX=REPO/'experiments/praxis_next'
PRIVATE=Path('C:/w/apt_benchmark_data_20260920/praxis_next')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def write(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def main():
    sources={}
    def bind(path,expected=None):
        digest=sha(path)
        if expected and expected!=digest:raise ValueError('Frozen source/receipt differs: '+str(path))
        sources[path.relative_to(REPO).as_posix()]=digest
    b80=read(PX/'px080_context_selector/results/COMPLETE.json')
    for relative,digest in b80['source_binding']['files'].items():bind(REPO/relative,digest)
    b81=read(PX/'px081_evidence_acquisition/FREEZE.json')
    for name,digest in b81['source_sha256'].items():bind(PX/'px081_evidence_acquisition'/name,digest)
    b82=read(PX/'px082_temporal_audit/COMPLETE.json')
    for name,digest in b82['source'].items():bind(PX/'px082_temporal_audit'/name,digest)
    b83=read(PX/'px083_policy_transfer/FREEZE.json')
    for name,digest in b83['binding']['files'].items():bind(PX/'px083_policy_transfer'/name,digest)
    for rel in ('px080_context_selector/results/COMPLETE.json','px080_context_selector/results/STARTED.json',
                'px081_evidence_acquisition/RUN_RECEIPT.json','px082_temporal_audit/COMPLETE.json','px082_temporal_audit/DESIGN.json',
                'px083_policy_transfer/results/COMPLETE.json','px083_policy_transfer/results/STARTED.json',
                'px083_policy_transfer/results/AUDIT.json'):
        bind(PX/rel)
    for name in ('protocol.json','run.py'):bind(REPO/'experiments/apt_benchmark/robustness_v2'/name)
    saved=[]
    def describe(model,path,experiment,key=None):
        entry={'experiment':experiment,'file':str(path),'file_sha256':sha(path),'bundle_key':key,
            'python_class':type(model).__name__,'features':int(model.n_features_in_),'parameters':model.get_params()}
        if hasattr(model,'booster_'):
            entry.update(actual_objective=model.objective_,actual_iterations=model.booster_.current_iteration(),
                actual_tree_count=model.booster_.num_trees(),booster_parameters=model.booster_.params)
        saved.append(entry)
    for path in sorted((PRIVATE/'px080/run_v1').glob('*/*.joblib')):
        describe(joblib.load(path),path,'PX080')
    for path in sorted((PRIVATE/'px081').glob('seed_*/models.joblib')):
        models=joblib.load(path)
        for role in ('classifiers','selectors'):
            for key,model in models[role].items():describe(model,path,'PX081',role+':'+str(key))
    for name in ('ordinary','target_cost'):
        path=PRIVATE/f'px083/run_v1/{name}.joblib';describe(joblib.load(path),path,'PX083')
    if (sum(i['experiment']=='PX080' for i in saved),sum(i['experiment']=='PX081' for i in saved),sum(i['experiment']=='PX083' for i in saved))!=(39,36,2):
        raise ValueError('Saved estimator inventory differs from expected retention')
    native=[]
    for dataset in ('casino','camlds'):
        root=PRIVATE.parents[0]/'robustness_v2'/(dataset+'_run1')
        # PRIVATE parent is apt_benchmark_data_20260920.
        protocol=read(root/'PROTOCOL.json');result=read(root/'RESULTS.json')
        for arm in ('semantic_event','entity_context','mixed_dropout'):
            path=root/f'T1105_{arm}.joblib'
            if sha(path)!=result['targets']['T1105']['models'][arm]['model_sha256']:
                raise ValueError('Native cached classifier hash mismatch')
            # The cached native models were fitted with a newer sklearn release.
            # Inspect stored attributes only; do not call cross-version prediction
            # or get_params (the constructor parameter names changed).
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always');model=joblib.load(path)['model']
            stored={k:getattr(model,k,None) for k in ('C','class_weight','solver','max_iter','random_state','penalty',
                'l1_ratio','fit_intercept','tol','intercept_scaling')}
            native.append(dict(dataset=dataset,arm=arm,model_sha256=sha(path),model_file=str(path),
                model_class=type(model).__name__,features=int(model.n_features_in_),stored_parameters=stored,
                original_sklearn_version=result['sklearn'],original_python_version=result['python'],
                metadata_only_loading_warnings=[str(w.message) for w in caught],prediction_called=False,
                declared_classifier=protocol['classifier'],text_features=protocol['text_features'],views=protocol['arms'][arm]['views'],
                source_protocol_sha256=sha(root/'PROTOCOL.json'),history=protocol['history']))
    records=[
        {'experiment':'PX080','role':'main history selection','new_classifier_fits':33,'new_regressor_fits':6,'new_fits_total':39,
         'count_derivation':'Per seed: 4 forward folds x 2 experts + 2 final experts + 1 augmented classifier + 2 regressors = 13; three seeds.',
         'fitting_seeds':[20260924,20260925,20260926],'classifier_parameters':b80['source_binding']['base_parameters'],
         'regressor_parameters':b80['source_binding']['selector_parameters'],'common_explicit_parameters':{'n_jobs':4,'deterministic':True,'force_col_wise':True,'verbosity':-1},
         'input_dimensions':{'current_roles':70,'context':108,'context_dropout':108,'selectors':20},
         'classifier_stage_weighted':False,'selector_costs':[1,1,4,4],
         'forward_targets':'w[y] * (I[context argmax != y] - I[current argmax != y]); ordinary uses w=1',
         'decision':'Use context only when predicted signed incremental loss <0; otherwise use current.',
         'selector_training_conditions':['clean','missing_half','stale_5min'],
         'evaluation_conditions':['clean','missing_half','missing_all','stale_5min','wrong_host'],
         'training_caps_per_class':[20000,5000,5000,5000],'meta_caps_per_class_per_capture':[12000,5000,5000,5000],
         'dropout':'One clean copy and one deterministic half-missing copy, sample weight0.5 each; same labels; GBDT, not DART.'},
        {'experiment':'PX081','role':'main evidence acquisition','new_classifier_fits':60,'new_regressor_fits':24,'new_fits_total':84,
         'count_derivation':'Per seed: 4 folds x 4 subset classifiers + 4 final classifiers + 4 legal transitions x 2 regressors = 28; three seeds.',
         'fitting_seeds':[8101,8102,8103],'classifier_parameters':{'n_estimators':150,'num_leaves':15,'learning_rate':.05,'min_child_samples':10,'reg_lambda':1},
         'regressor_parameters':{'n_estimators':100,'num_leaves':9,'learning_rate':.05,'min_child_samples':20,'reg_lambda':1},
         'common_explicit_parameters':{'n_jobs':2,'verbosity':-1},'deterministic_flag_explicit':False,'force_col_wise_explicit':False,
         'input_dimensions':{'current':62,'current_roles':70,'current_history':98,'current_roles_history':106,'selector_state0':66,'selector_state1':74,'selector_state2':102},
         'classifier_stage_weighted':False,'selector_costs':[1,1,4,4],
         'harm_target':'weighted 0/1 loss before minus after acquisition; positive means favorable',
         'entropy_target':'natural-log entropy before minus after acquisition; positive means lower predictive entropy',
         'gain_score':'predicted gain * declared availability prior / channel cost',
         'costs':{'roles':1,'history':2},'nominal_delays':{'roles':.25,'history':.75},'deadline':1,'budgets':[1,2,3],
         'availability_prior_delayed':{'roles':.8,'history':.65},'availability_prior_other':{'roles':1,'history':1},
         'delayed_additional_delay_values':[0,.5,1.5],'delayed_additional_delay_probabilities':[.6,.25,.15],
         'max_acquisitions':2,'transition_state_channel_pairs':[[0,0],[0,1],[1,1],[2,0]],
         'training_and_selector_caps_per_class':[12000,4000,4000,4000],
         'interpretation':'Greedy one-step predicted utility heuristic. Regime priors supplied by simulation condition; no learned delay distribution, calibrated risk bound, or global planner.'},
        {'experiment':'PX082','role':'main temporal composition audit','new_classifier_fits':18,'new_regressor_fits':0,'new_fits_total':18,
         'count_derivation':'3 fitting seeds x 2 feature views x 3 training/test protocols.',
         'fitting_seeds':[20260923,20260924,20260925],'classifier_parameters':read(PX/'px082_temporal_audit/protocol.json')['model'],
         'other_explicit_parameters':{'deterministic':True,'force_col_wise':True,'verbosity':-1},
         'input_dimensions':{'current':62,'current_history':98},'matched_fit_counts':[20000,5000,20,1740],
         'classifier_stage_weighted':False,'calibrated_probabilities':False,'decision':'argmax over four declared evaluation classes',
         'saved_estimator_limit':'No serialized fitted estimators in this experiment; source/protocol/fit receipts/probabilities establish configurations and18fits.'},
        {'experiment':'PX083','role':'supplementary T1105 score-policy transfer, a different binary task','new_classifier_fits':0,'new_regressor_fits':2,'new_fits_total':2,
         'count_derivation':'One ordinary and one target-cost Ridge fit; same Casino calibration matrix. No new native classifier fit.',
         'fitting_seeds':None,'estimator':'sklearn.linear_model.Ridge','parameters':{'alpha':10.,'solver':'svd','fit_intercept':True},
         'input_dimensions':12,'feature_scaling':None,'fitting_rows':1494,'fitting_positive_rows':87,'nonzero_comparison_targets':11,
         'fitting_split':'Casino clean calibration','target':'T1105 Ingress Tool Transfer vs other author techniques',
         'regression_target':'w[y]*(I[h>0.5 != y]-I[c>0.5 != y]), w[positive]=1 or4, w[negative]=1',
         'classifier_decision':'strict score>0.5; tie is negative','selector_decision':'context when linear Ridge score<0; tie uses current',
         'native_classifier_family':'Previously fitted class-balanced binary LogisticRegression; three reused controls per dataset.',
         'native_classifier_transferred':False,'selector_transferred_unchanged':True,'test_views_per_dataset':21,'dataset_count':2,'prediction_tables':294,
         'interpretation':'Two deterministic Ridge fits, not three training seeds. Perturbation seeds are repeated views. Negatives are not verified benign traffic.'}
    ]
    assert sum(r['new_fits_total'] for r in records)==143
    assert sum(r['new_classifier_fits'] for r in records)==111
    output=dict(status='READ_ONLY_MODEL_IMPLEMENTATION_AUDIT',created_utc=datetime.now(timezone.utc).isoformat(),
        versions={k:importlib.metadata.version(k) for k in ('lightgbm','scikit-learn','numpy')},
        totals={'main_lightgbm_fits':141,'main_classifier_fits':111,'main_regressor_fits':30,'supplementary_ridge_fits':2,'new_fits_this_audit':0,
                'reused_T1105_native_models':6,'reused_native_models_counted_as_new':False},
        common_library_defaults={'classifier':LGBMClassifier().get_params(),'regressor':LGBMRegressor().get_params()},
        iteration_note='n_estimators is boosting iterations; four-class multiclass builds class-specific trees. Counts here are fitted estimators, not individual trees.',
        experiments=records,source_sha256=sources,saved_estimators_inspected=saved,reused_native_estimators_inspected=native,
        not_run_in_PX080_to_PX083=['TabM','GNN/graph neural network','GML architecture or mathematical modification','LLM/Qwen classifier or verifier','SVM','SEFA implementation','Learning-to-Measure implementation','reinforcement-learning evidence planner'],
        classification_warning='Stage-weighted loss targets do not mean class-weighted LightGBM experts. Probability-like outputs were not post-hoc calibrated in the main experiments.',
        source_locations={'PX080':'experiments/praxis_next/px080_context_selector/run.py:73-92,133-177',
            'PX081':'experiments/praxis_next/px081_evidence_acquisition/run.py:33-59,85-112,156-183',
            'PX082':'experiments/praxis_next/px082_temporal_audit/run.py:108-125; protocol.json:model',
            'PX083':'experiments/praxis_next/px083_policy_transfer/run.py:74-108; robustness_v2/run.py:54-60,199-229'})
    write(HERE/'MODEL_INVENTORY.json',output)
    print(json.dumps({'status':'PASS','new_fits':0,'retained_estimators_inspected':len(saved),'reused_native_estimators_inspected':len(native),'fit_totals':output['totals']},indent=2))


if __name__=='__main__':main()
