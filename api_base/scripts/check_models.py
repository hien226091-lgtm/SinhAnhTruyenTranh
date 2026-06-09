#!/usr/bin/env python3
"""
Check which Vertex AI models are accessible and classify
which models are image-capable and which look specialized for comics.

Usage examples:
    python api_base/scripts/check_models.py
  # PowerShell example:
    # $env:VERTEX_PROJECT_ID = "your-gcp-project-id"; python api_base/scripts/check_models.py

Outputs a JSON file `api_base/outputs/models_accessible.json` with categories.
"""
import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

REPO_ROOT = Path(__file__).resolve().parents[2]
API_BASE_DIR = REPO_ROOT / "api_base"
if str(API_BASE_DIR) not in sys.path:
        sys.path.insert(0, str(API_BASE_DIR))

from api_base.app.config import CONFIG
from google import genai
from google.auth.exceptions import DefaultCredentialsError


IMAGE_KEYWORDS = [
    "image",
    "img",
    "dall",
    "dalle",
    "stable",
    "sd",
    "sdxl",
    "vision",
    "clip",
    "img2img",
    "render",
    "midjourney",
    "mj",
    "diffusion",
    "illustration",
    "bison",
    "vision",
]

COMIC_KEYWORDS = [
    "comic",
    "manga",
    "cartoon",
    "anime",
    "toon",
    "illustration",
    "lineart",
    "comicgen",
]


def _build_vertex_client() -> genai.Client:
    if not CONFIG.vertex_project_id:
        raise RuntimeError("Missing VERTEX_PROJECT_ID or GOOGLE_CLOUD_PROJECT in .env")
    try:
        return genai.Client(**CONFIG.build_vertex_client_kwargs())
    except Exception as exc:
        raise RuntimeError(
            "Missing Vertex AI credentials. Set VERTEX_CREDENTIALS_FILE or GOOGLE_APPLICATION_CREDENTIALS to a service-account JSON, or run 'gcloud auth application-default login'."
        ) from exc


def get_vertex_models() -> List[Dict[str, Any]]:
    client = _build_vertex_client()
    models: List[Dict[str, Any]] = []

    for model in client.models.list():
        if isinstance(model, dict):
            model_id = model.get("name") or model.get("id") or model.get("model_id") or ""
            description = model.get("description") or model.get("display_name") or model.get("displayName") or ""
            models.append({"id": model_id, "description": description, **model})
            continue

        model_id = getattr(model, "name", None) or getattr(model, "id", None) or getattr(model, "model_id", None) or str(model)
        description = getattr(model, "description", None) or getattr(model, "display_name", None) or getattr(model, "displayName", None) or ""
        models.append({"id": model_id, "description": description, "raw": model})

    return models


def text_has_keyword(text: str, keywords: List[str]) -> bool:
    t = (text or "").lower()
    return any(k in t for k in keywords)


def classify_model(model_obj: Dict[str, Any]) -> str:
    model_id = str(model_obj.get("id", model_obj.get("name", ""))).lower()
    description = str(model_obj.get("description", model_obj.get("displayName", ""))).lower()

    is_comic = text_has_keyword(model_id, COMIC_KEYWORDS) or text_has_keyword(description, COMIC_KEYWORDS)
    is_image = text_has_keyword(model_id, IMAGE_KEYWORDS) or text_has_keyword(description, IMAGE_KEYWORDS)

    if is_comic:
        return "comic"
    if is_image:
        return "image"
    return "other"


def build_report(models: List[Dict[str, Any]]) -> Dict[str, Any]:
    report = {"models": [], "by_category": {"comic": [], "image": [], "other": []}}
    for m in models:
        mid = m.get("id") if isinstance(m, dict) else str(m)
        category = classify_model(m if isinstance(m, dict) else {"id": mid})
        entry = {"id": mid, "category": category}
        # include short description if present
        if isinstance(m, dict) and "description" in m:
            entry["description"] = m.get("description")
        report["models"].append(entry)
        report["by_category"][category].append(entry)
    return report


def save_report(report: Dict[str, Any], out_path: str) -> None:
    out_dir = os.path.dirname(out_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def main():
    p = argparse.ArgumentParser(description="List accessible Vertex AI models and classify comic/image models.")
    p.add_argument("--output", default="api_base/outputs/models_accessible.json", help="Output JSON file path")
    args = p.parse_args()

    try:
        models = get_vertex_models()
    except Exception as e:
        message = str(e)
        lowered = message.lower()
        if "default credentials were not found" in lowered or "application default credentials" in lowered:
            print(
                "ERROR: Missing Vertex AI credentials. Set VERTEX_CREDENTIALS_FILE or GOOGLE_APPLICATION_CREDENTIALS to a service-account JSON, or run 'gcloud auth application-default login'.",
                file=sys.stderr,
            )
        else:
            print(f"Error while fetching Vertex models: {e}", file=sys.stderr)
        sys.exit(3)

    report = build_report(models)
    save_report(report, args.output)
    print(f"Saved model report to {args.output}")
    for cat in ("comic", "image", "other"):
        items = report['by_category'].get(cat, [])
        print(f"{cat}: {len(items)}")
        for it in items:
            mid = it.get('id')
            desc = it.get('description', '')
            # Print short one-line summary
            if desc:
                print(f"  - {mid}: {desc}")
            else:
                print(f"  - {mid}")


if __name__ == "__main__":
    main()
