"""Legacy package.

Historically the application lived under ``app.legacy``. The current codebase
is the NCP-aligned platform under ``app.platform`` and keeps a small set of
compatibility shims (``app.models``, ``app.routers``, ``app.utils``) that
re-export from here. Only the logging utility is required by the active
platform code path.
"""
