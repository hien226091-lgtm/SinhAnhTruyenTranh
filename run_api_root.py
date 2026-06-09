"""Root launcher to run FastAPI app from project root."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import os

import uvicorn

# Set GOOGLE_APPLICATION_CREDENTIALS BEFORE importing anything else
if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\VoVanHien\AppData\Roaming\gcloud\application_default_credentials.json"


def parse_args() -> argparse.Namespace:
    """Parse CLI options for launching the API server."""
    parser = argparse.ArgumentParser(description="Run FastAPI server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    parser.add_argument(
        "--reload",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable or disable auto-reload",
    )
    parser.add_argument(
        "--app",
        default="app.main:app",
        help="ASGI app import path (e.g. app.main:app)",
    )
    return parser.parse_args()


def main() -> None:
    """Run API application from the root directory."""
    args = parse_args()
    root_dir = Path(__file__).resolve().parent
    api_base_dir = root_dir / "api_base"
    sys.path.insert(0, str(api_base_dir))

    uvicorn.run(args.app, host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
