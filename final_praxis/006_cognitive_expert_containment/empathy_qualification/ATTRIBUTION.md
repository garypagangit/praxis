# Attribution and reproduction notes

Data: Blablablab/SOCKET, empathy#empathy_bin at immutable revision beb92deb932d67a6319cc7ca71d8056ececc47d2. Validation selection and JSON reformatting are our changes. The dataset card and original Empathic Reactions repository declare CC BY 4.0. Retain source attribution and license notice with the redistributed small fixture. No ownership of participant statements is claimed.

- Buechel et al. (2018), *Modeling Empathy and Distress in Reaction to News Stories*: https://arxiv.org/abs/1808.10399 ; original data/notice: https://github.com/wwbp/empathic_reactions
- Choi et al. (2023), SOCKET: https://github.com/minjechoi/SOCKET ; pinned dataset: https://huggingface.co/datasets/Blablablab/SOCKET/tree/beb92deb932d67a6319cc7ca71d8056ececc47d2
- CC BY 4.0 license: https://creativecommons.org/licenses/by/4.0/
- Exact SOCKET question and No/Yes option order: https://github.com/minjechoi/SOCKET/blob/2f4fffff01a591346bf823df59a515eabb764b1d/experiments/zeroshot/socket_prompts.csv
- MiCRo v3: https://arxiv.org/html/2506.13331v3
- Exact three demonstration pairs: https://github.com/BKHMSI/mixture-of-cognitive-reasoners/blob/275a5e4b1369ff19c8e3f33f42f16bc5ef19e6d7/benchmarks/empathy.py ; fewshot_samples extracted as literal data with ast.literal_eval, without importing that source.
- Source chat rendering uses tokenizer.apply_chat_template with add_generation_prompt=True: https://github.com/BKHMSI/mixture-of-cognitive-reasoners/blob/275a5e4b1369ff19c8e3f33f42f16bc5ef19e6d7/generate.py
- Existing checkpoint: https://huggingface.co/bkhmsi/micro-smollm2-135m/tree/1ebfb28c382f9176647bbbb9f63cdb7ed0a62e57

The checkpoint/custom repository redistribution license remains unverified. This folder contains a new small harness and an attributed prompt extract; it neither redistributes model weights nor copies custom model architecture. Prompt/data licensing and exact SOCKET binarization provenance must be resolved for a public research release. These reuse notes do not require another user permission request for the already authorized internal technical evaluation.

prepare.py verifies previously acquired public source hashes and reads only validation files plus source prompt material. It performs no network calls. run_empathy.py defaults to manifest validation without importing the model loader. Real execution requires --execute and matching PRAXIS_PREREG_PATH / PRAXIS_PREREG_SHA256 environment values.

```powershell
python prepare.py --source-dir ../006_nextdata --out data
python -m unittest discover -s . -p test_empathy.py -v
python run_empathy.py --data data --arc-runner <qualified_arc_run_arc.py> --qualification <qualification-dir> --previous-out <successful-original-qualification-output> --out <new-run-output>
```

Root reviews/freezes the preregistration and chooses the AWS launch. Add --execute only for that approved bounded launch. Preparation, tests, and source verification involve no actual model inference or AWS calls.
