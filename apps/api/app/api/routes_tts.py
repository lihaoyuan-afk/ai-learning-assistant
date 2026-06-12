from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import Response

from app.api.deps import CurrentUserID

router = APIRouter(prefix="/tts", tags=["tts"])


@router.post("")
def synthesize(text: str = Body(..., embed=True), user_id: CurrentUserID = None) -> Response:
    """Convert text to MP3 audio. Requires an OpenAI-compatible TTS endpoint."""
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="text 不能为空")

    from app.services.tts_service import text_to_speech
    try:
        audio = text_to_speech(text)
    except (RuntimeError, Exception) as exc:
        raise HTTPException(
            status_code=503,
            detail=f"语音合成不可用（需要支持 TTS 的 OpenAI 端点）: {exc}",
        )

    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=speech.mp3"},
    )
