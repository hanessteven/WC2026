---
name: feedback-no-init-files
description: Don't create __init__.py in src/ or tests/ directories
metadata:
  type: feedback
---

Don't create `__init__.py` files in `src/` or `tests/` directories.

**Why:** User preference — not needed for this project structure.

**How to apply:** Skip `__init__.py` creation when scaffolding packages in this project.