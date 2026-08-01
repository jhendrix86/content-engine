"""
Real AI content generation via the OpenAI v1 SDK.

Mirrors the pattern used in media-generation-service/app/services/api_engine.py:
call the real provider, and report an honest, structured failure (rather than
fabricating output) when it can't run - e.g. no API key configured.
"""

from typing import Any, Dict, Optional

from loguru import logger
from openai import AsyncOpenAI

from app.config import settings
from app.models.content import ContentType

_TYPE_INSTRUCTIONS = {
    ContentType.BLOG_POST: "Write a well-structured blog post with a clear introduction, body, and conclusion.",
    ContentType.SOCIAL_MEDIA: "Write a short, engaging social media post.",
    ContentType.EMAIL_COPY: "Write persuasive marketing email copy with a clear call to action.",
    ContentType.LANDING_PAGE: "Write landing page copy: a headline, supporting copy, and a call to action.",
    ContentType.VIDEO_SCRIPT: "Write a video script with scene directions and spoken lines.",
    ContentType.PRODUCT_DESCRIPTION: "Write a compelling product description highlighting key benefits.",
}


class AIWriter:
    """Generates content via OpenAI, or reports honestly why it couldn't."""

    def __init__(self):
        self._client: Optional[AsyncOpenAI] = (
            AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        )

    async def generate(
        self,
        content_type: ContentType,
        topic: str,
        target_audience: Optional[str] = None,
        tone: Optional[str] = None,
        length: Optional[int] = None,
    ) -> Dict[str, Any]:
        if self._client is None:
            logger.warning("AI writer called with no OpenAI API key configured")
            return {
                "success": False,
                "error": "OpenAI API key not configured",
                "model": settings.ai_model,
            }

        instructions = _TYPE_INSTRUCTIONS.get(content_type, "Write high-quality marketing content.")
        prompt_parts = [instructions, f"Topic: {topic}"]
        if target_audience:
            prompt_parts.append(f"Target audience: {target_audience}")
        if tone:
            prompt_parts.append(f"Tone: {tone}")
        if length:
            prompt_parts.append(f"Target length: approximately {length} words.")
        prompt = "\n".join(prompt_parts)

        try:
            response = await self._client.chat.completions.create(
                model=settings.ai_model,
                messages=[
                    {"role": "system", "content": "You are an expert marketing content writer."},
                    {"role": "user", "content": prompt},
                ],
            )
            body = response.choices[0].message.content or ""
            return {
                "success": True,
                "body": body,
                "model": settings.ai_model,
                "prompt": prompt,
            }
        except Exception as e:
            logger.error(f"AI content generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "model": settings.ai_model,
                "prompt": prompt,
            }
