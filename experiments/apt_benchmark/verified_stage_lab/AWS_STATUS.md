# Compute and AWS status

September 22, 2026.

The requested experiment completed on the local Windows CPU. Collection took **255.93 seconds** and the **21 LightGBM fits plus scoring took 15.46 seconds**. A GPU was unnecessary for this workload.

AWS access was attempted using the existing `praxis-build` profile. STS rejected the expired SSO session. A device sign-in was initiated and the user was given its sign-in instructions; the login process subsequently failed to reach the OIDC token endpoint. A final STS retry still reported an expired or invalid SSO session. No successful refreshed authentication was observed.

**No AWS compute, storage upload, or quota change was initiated for this experiment.** Current cloud inventory could not be inspected with the expired session. An earlier observation that a GPU instance was stopped is historical and does not establish its current state. The experiment does not claim a cloud run or a verified account-wide spend total.

The run receipt records Python 3.11.9, NumPy 2.2.6, LightGBM 4.6.0, scikit-learn 1.7.2, and joblib 1.6.0. The collection and models completed without waiting for cloud access. Raw transactions, model files, and row-level predictions are retained in the private local experiment directory; sanitized results and reproducible source are published in Git.
