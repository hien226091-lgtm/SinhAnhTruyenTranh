"""Base routes such as health check."""

from fastapi import APIRouter

from api_base.app.models.schemas import HealthResponse


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Basic health check endpoint."""
    return HealthResponse(status="ok")


@router.post("/produce")
def produce_mock(payload: dict) -> dict:
    """Mock AI produce endpoint used by the Studio front-end during UI testing.

    This returns a small array of frame metadata so the UI can render previews
    without requiring the real image-generation backend to be available.
    """
    # Determine number of frames from layout or a default of 4
    frames_count = 4
    try:
        layout = payload.get("layout") if isinstance(payload, dict) else None
        if isinstance(layout, list) and len(layout) > 0:
            frames_count = min(12, max(1, len(layout)))
        else:
            # If script contains multiple paragraphs, use that as guidance
            script = (payload.get("script") or "") if isinstance(payload, dict) else ""
            paras = [p for p in script.split("\n\n") if p.strip()]
            if paras:
                frames_count = min(12, max(1, len(paras)))
    except Exception:
        frames_count = 4

    frames = []
    for i in range(frames_count):
        frames.append(
            {
                "FrameOrder": i + 1,
                "ImageDescription": f"Demo description for frame {i+1}",
                "GenerationStatus": "done",
                # Use a simple placeholder image so the UI shows thumbnails
                "GeneratedImageUrl": f"https://via.placeholder.com/640x360.png?text=Frame+{i+1}",
            }
        )

    return {"frames": frames}
