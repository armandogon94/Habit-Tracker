"""Pytest session setup.

Application settings (``app.core.config``) intentionally have NO insecure
defaults: ``JWT_SECRET`` and ``DATABASE_URL`` must be supplied by the
environment or startup fails fast. Importing the app modules constructs
``Settings()`` at import time, so inject safe, deterministic test values here
*before* any app module is imported. ``setdefault`` keeps real CI/dev values
authoritative when they are already present.
"""

import os

os.environ.setdefault("JWT_SECRET", "test-secret-key-not-for-production-min-32-chars")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/habits_test",
)
