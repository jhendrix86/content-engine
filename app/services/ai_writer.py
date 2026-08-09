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

_REPURPOSE_INSTRUCTIONS = {
    ContentType.BLOG_POST: "Rewrite the following source material as a well-structured blog post with a clear introduction, body, and conclusion. Do not just summarize it - expand it into a standalone piece.",
    ContentType.SOCIAL_MEDIA: "Extract the single most compelling idea from the following source material and turn it into a short, engaging social media post. Do not try to cover everything.",
    ContentType.EMAIL_COPY: "Rewrite the following source material as persuasive marketing email copy with a clear call to action.",
    ContentType.LANDING_PAGE: "Rewrite the following source material as landing page copy: a headline, supporting copy, and a call to action.",
    ContentType.VIDEO_SCRIPT: "Adapt the following source material into a video script with scene directions and spoken lines.",
    ContentType.PRODUCT_DESCRIPTION: "Rewrite the following source material as a compelling product description highlighting key benefits.",
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

    async def repurpose(
        self,
        source_body: str,
        target_type: ContentType,
        target_audience: Optional[str] = None,
        tone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a derivative piece in a different format from existing source content."""
        if self._client is None:
            logger.warning("AI writer repurpose called with no OpenAI API key configured")
            return {
                "success": False,
                "error": "OpenAI API key not configured",
                "model": settings.ai_model,
            }

        instructions = _REPURPOSE_INSTRUCTIONS.get(target_type, "Repurpose the following source material into new marketing content.")
        prompt_parts = [instructions]
        if target_audience:
            prompt_parts.append(f"Target audience: {target_audience}")
        if tone:
            prompt_parts.append(f"Tone: {tone}")
        prompt_parts.append(f"Source material:\n{source_body}")
        prompt = "\n".join(prompt_parts)

        try:
            response = await self._client.chat.completions.create(
                model=settings.ai_model,
                messages=[
                    {"role": "system", "content": "You are an expert marketing content writer specializing in repurposing content across formats."},
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
            logger.error(f"AI content repurposing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "model": settings.ai_model,
                "prompt": prompt,
            }
