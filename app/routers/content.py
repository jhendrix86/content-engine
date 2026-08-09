"""
Content router
"""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from loguru import logger

from app.database import get_db
from app.models.content import Content, ContentType, ContentStatus
from app.services.ai_writer import AIWriter
from app.utils.serializers import model_to_dict

router = APIRouter()


def get_ai_writer(request: Request) -> AIWriter:
    return request.app.state.ai_writer


class GenerateContentRequest(BaseModel):
    """Request to generate content"""
    title: str
    content_type: ContentType
    topic: str
    target_audience: Optional[str] = None
    tone: Optional[str] = None
    length: Optional[int] = None


class UpdateContentRequest(BaseModel):
    """Request to update content"""
    title: Optional[str] = None
    body: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[ContentStatus] = None


class RepurposeContentRequest(BaseModel):
    """Request to repurpose an existing piece of content into other formats"""
    target_types: List[ContentType]


@router.post("/generate")
async def generate_content(
    request: GenerateContentRequest,
    db: AsyncSession = Depends(get_db),
    ai_writer: AIWriter = Depends(get_ai_writer)
):
    """Generate content with AI"""
    try:
        logger.info(f"Generating content: {request.title}")

        result = await ai_writer.generate(
            content_type=request.content_type,
            topic=request.topic,
            target_audience=request.target_audience,
            tone=request.tone,
            length=request.length,
        )

        content = Content(
            title=request.title,
            content_type=request.content_type,
            status=ContentStatus.READY if result["success"] else ContentStatus.DRAFT,
            body=result.get("body"),
            topic=request.topic,
            target_audience=request.target_audience,
            tone=request.tone,
            length=request.length,
            ai_model=result.get("model"),
            generation_prompt=result.get("prompt"),
            extra_metadata={"generation_result": result},
        )

        db.add(content)
        await db.commit()
        await db.refresh(content)

        logger.info(f"Content generated: {content.id}")
        return model_to_dict(content)

    except Exception as e:
        logger.error(f"Failed to generate content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{content_id}/repurpose")
async def repurpose_content(
    content_id: str,
    request: RepurposeContentRequest,
    db: AsyncSession = Depends(get_db),
    ai_writer: AIWriter = Depends(get_ai_writer)
):
    """Generate derivative content in other formats from an existing 'pillar' piece"""
    try:
        logger.info(f"Repurposing content {content_id} into {[t.value for t in request.target_types]}")

        source = await db.get(Content, uuid.UUID(content_id))
        if source is None:
            raise HTTPException(status_code=404, detail=f"Content not found: {content_id}")
        if not source.body:
            raise HTTPException(status_code=400, detail="Source content has no body to repurpose")

        derivatives = []
        for target_type in request.target_types:
            result = await ai_writer.repurpose(
                source_body=source.body,
                target_type=target_type,
                target_audience=source.target_audience,
                tone=source.tone,
            )

            derivative = Content(
                title=f"{source.title} ({target_type.value})",
                content_type=target_type,
                status=ContentStatus.READY if result["success"] else ContentStatus.DRAFT,
                body=result.get("body"),
                source_content_id=source.id,
                topic=source.topic,
                target_audience=source.target_audience,
                tone=source.tone,
                ai_model=result.get("model"),
                generation_prompt=result.get("prompt"),
                extra_metadata={"generation_result": result, "repurposed_from": str(source.id)},
            )
            db.add(derivative)
            derivatives.append(derivative)

        await db.commit()
        for derivative in derivatives:
            await db.refresh(derivative)

        logger.info(f"Repurposed {len(derivatives)} derivative(s) from {content_id}")
        return {
            "source_content_id": str(source.id),
            "derivatives": [model_to_dict(d) for d in derivatives],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to repurpose content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{content_id}")
async def get_content(
    content_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get content details"""
    try:
        logger.info(f"Getting content details for {content_id}")

        content = await db.get(Content, uuid.UUID(content_id))
        if content is None:
            raise HTTPException(status_code=404, detail=f"Content not found: {content_id}")

        return model_to_dict(content)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{content_id}/derivatives")
async def list_derivatives(
    content_id: str,
    db: AsyncSession = Depends(get_db)
):
    """List all content repurposed from this piece"""
    try:
        logger.info(f"Listing derivatives of {content_id}")

        source = await db.get(Content, uuid.UUID(content_id))
        if source is None:
            raise HTTPException(status_code=404, detail=f"Content not found: {content_id}")

        result = await db.execute(
            select(Content).where(Content.source_content_id == source.id).order_by(Content.created_at.desc())
        )
        derivatives = [model_to_dict(d) for d in result.scalars().all()]

        return {"source_content_id": str(source.id), "total": len(derivatives), "derivatives": derivatives}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list derivatives: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_content(
    content_type: Optional[ContentType] = None,
    status: Optional[ContentStatus] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List content"""
    try:
        logger.info("Listing content")

        query = select(Content)
        if content_type is not None:
            query = query.where(Content.content_type == content_type)
        if status is not None:
            query = query.where(Content.status == status)

        count_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()

        query = query.order_by(Content.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(query)
        items = [model_to_dict(c) for c in result.scalars().all()]

        return {
            "total": total,
            "content": items,
            "filters": {
                "content_type": content_type.value if content_type else None,
                "status": status.value if status else None
            },
            "pagination": {
                "limit": limit,
                "offset": offset
            }
        }

    except Exception as e:
        logger.error(f"Failed to list content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{content_id}")
async def update_content(
    content_id: str,
    request: UpdateContentRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update content"""
    try:
        logger.info(f"Updating content {content_id}")

        content = await db.get(Content, uuid.UUID(content_id))
        if content is None:
            raise HTTPException(status_code=404, detail=f"Content not found: {content_id}")

        for field, value in request.model_dump(exclude_unset=True).items():
            setattr(content, field, value)

        await db.commit()
        await db.refresh(content)

        return model_to_dict(content)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{content_id}/publish")
async def publish_content(
    content_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Mark content as published"""
    try:
        logger.info(f"Publishing content {content_id}")

        content = await db.get(Content, uuid.UUID(content_id))
        if content is None:
            raise HTTPException(status_code=404, detail=f"Content not found: {content_id}")

        content.status = ContentStatus.PUBLISHED
        content.published_at = datetime.utcnow()
        await db.commit()
        await db.refresh(content)

        return model_to_dict(content)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to publish content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{content_id}")
async def delete_content(
    content_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete content"""
    try:
        logger.info(f"Deleting content {content_id}")

        content = await db.get(Content, uuid.UUID(content_id))
        if content is None:
            raise HTTPException(status_code=404, detail=f"Content not found: {content_id}")

        await db.delete(content)
        await db.commit()

        return {"id": content_id, "deleted": True, "deleted_at": datetime.utcnow().isoformat()}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete content: {e}")
        raise HTTPException(status_code=500, detail=str(e))
