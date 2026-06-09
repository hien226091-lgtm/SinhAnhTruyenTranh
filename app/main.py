"""Proxy module so `uvicorn app.main:app` imports the actual app from `api_base`.
"""

from api_base.app.main import app  # re-export app

__all__ = ["app"]
