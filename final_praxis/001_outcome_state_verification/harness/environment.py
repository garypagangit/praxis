from copy import deepcopy
from .task_registry import get_task

class InertEnvironment:
    def __init__(self, task_id):
        self.spec = get_task(task_id)
        self.state = deepcopy(self.spec.initial_state)

    def snapshot(self):
        return deepcopy(self.state)
