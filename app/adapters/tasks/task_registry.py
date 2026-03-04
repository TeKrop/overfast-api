"""Task registry — shared TASK_MAP populated by worker.py at startup.

Keeping this in a separate module breaks the circular import chain:
  worker.py → dependencies.py → valkey_task_queue.py → task_registry.py
                                                         (no dep on worker.py)
"""

from typing import Any

# Populated by worker.py once the broker.task-decorated functions are defined.
TASK_MAP: dict[str, Any] = {}
