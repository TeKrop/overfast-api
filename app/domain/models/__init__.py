"""Domain models package.

Domain model classes (dataclasses or Pydantic models representing core business
entities independently of FastAPI response schemas) will live here from Phase 5
onward, when background refresh workers need structured types to pass between
the task queue and the service layer.

The folder is intentionally empty during Phase 4 — all response shapes are
currently expressed directly via the existing Pydantic models in each feature
module (e.g. app/heroes/models.py).
"""
