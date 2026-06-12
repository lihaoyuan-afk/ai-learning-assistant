"""Text-to-speech via OpenAI TTS API."""

from app.core.config import settings

_MAX_CHARS = 4096  # OpenAI TTS per-request character limit


def text_to_speech(text: str) -> bytes:
    """Convert text to MP3 bytes. Raises RuntimeError if TTS not available."""
    from openai import OpenAI

    if not text or not text.strip():
        raise ValueError("Empty text")

    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url or None,
        timeout=60,
    )
    try:
        response = client.audio.speech.create(
            model=settings.tts_model,
            voice=settings.tts_voice,  # type: ignore[arg-type]
            input=text.strip()[:_MAX_CHARS],
            response_format="mp3",
        )
        return response.content
    except Exception as exc:
        raise RuntimeError(f"TTS failed: {exc}") from exc
