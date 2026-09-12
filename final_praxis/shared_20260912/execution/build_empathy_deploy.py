from pathlib import Path
import hashlib
here=Path(__file__).resolve().parent
text=(here/'deploy006arc.sh').read_text(encoding='utf-8')
old_command='"$scratch/venv006/bin/python" "$study/arc_qualification/run_arc.py" --data "$study/arc_qualification/data" --qualification "$study/qualification" --previous-out "$scratch/fp006-20260912-11227b8/outputs" --out "$runroot/outputs" --execute'
new_command='"$scratch/venv006/bin/python" "$study/empathy_qualification/run_empathy.py" --data "$study/empathy_qualification/data" --arc-runner "$study/arc_qualification/run_arc.py" --qualification "$study/qualification" --previous-out "$scratch/fp006-20260912-11227b8/outputs" --out "$runroot/outputs" --execute'
assert old_command in text
text=text.replace(old_command,new_command)
changes={'fp006-arc-20260912-6372d09':'fp006-empathy-20260912-5c33bc4','fp006-arc-6372d09.zip':'fp006-empathy-5c33bc4.zip','9efd8f69902bb4e64278976748f5e70c7bfdcadb349f85e2215887b98a6b0dab':'f462d06b62dcff96175157ab73e138f56fc6a5ede36877ed25b38215684d8eac','praxis006-arc':'praxis006-empathy','RuntimeMaxSec=2700':'RuntimeMaxSec=1920','--seconds 2400':'--seconds 1800','arc_qualification/PREREGISTRATION.md':'empathy_qualification/PREREGISTRATION.md','7d35d4b592373daaa16320f7700cafa127e8717104e35361f5fa99194a6d16f5':hashlib.sha256(Path('C:/w/fp006/final_praxis/006_cognitive_expert_containment/empathy_qualification/PREREGISTRATION.md').read_bytes()).hexdigest()}
for before,after in changes.items():assert before in text;text=text.replace(before,after)
(here/'deploy006empathy.sh').write_text(text,encoding='utf-8',newline='\n')
print(here/'deploy006empathy.sh')
