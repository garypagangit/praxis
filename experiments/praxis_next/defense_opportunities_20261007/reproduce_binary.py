"""Refit both binary sensitivities directly from published converted records."""
import shutil
from threadpoolctl import threadpool_limits
from screen import HERE
import binary as b
b.HERE=HERE
with threadpool_limits(limits=1):
 b.run(HERE/'evidence/REPLAY_INPUT.json')
 for name in ['BINARY_RESULTS.json','BINARY_PREDICTIONS.json']:
  shutil.copyfile(HERE/'evidence'/name,HERE/'evidence'/('UNFILTERED_'+name))
 b.run(HERE/'evidence/FILTERED_REPLAY_INPUT.json')
