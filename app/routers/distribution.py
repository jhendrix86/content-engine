"""
Distribution router

Note: there is no real social/platform posting client anywhere in this
codebase (no Twitter/LinkedIn/Facebook API wrapper). /publish records a real
Distribution row (scheduled or pending); /{id}/execute attempts the actual
post and honestly reports status=FAILED with a clear reason, rather than
faking a successful platform publish. Wiring a real platform client is a
separate feature-build task.
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from loguru import logger

from app.database import get_db
from app.models.content import Content
from app.models.distribution import Distribution, DistributionStatus
from app.utils.serializers import model_to_dict

router = APIRouter()

_NO_PLATFORM_CLIENT_MESSAGE = "No platform posting client is configured for this service yet."


class PublishRequest(BaseModel):
    """Request to distribute content to a platform"""
    content_id: str
    platform: str
    scheduled_at: Optional[datetime] = None


@router.post("/publish")
async def publish(
    request: PublishRequest,
    db: AsyncSession = Depends(get_db)
):
    """Record a distribution request for a content item to a platform"""
    try:
        logger.info(f"Recording distribution: content={request.content_id} platform={request.platform}")

        content = await db.get(Content, uuid.UUID(request.content_id))
        if content is None:
            raise HTTPException(status_code=404, detail=f"Content not found: {request.content_id}")

        distribution = Distribution(
            content_id=content.id,
            platform=request.platform,
            status=DistributionStatus.SCHEDULED if request.scheduled_at else DistributionStatus.PENDING,
            scheduled_at=request.scheduled_at,
        )
        db.add(distribution)
        await db.commit()
        await db.refresh(distribution)

        return model_to_dict(distribution)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to record distribution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{distribution_id}/execute")
async def execute_distribution(
    distribution_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Attempt to actually publish a pending distribution to its platform"""
    try:
        logger.info(f"Executing distribution {distribution_id}")

        distribution = await db.get(Distribution, uuid.UUID(distribution_id))
        if distribution is None:
            raise HTTPException(status_code=404, detail=f"Distribution not found: {distribution_id}")

        distribution.status = DistributionStatus.FAILED
        distribution.error_message = _NO_PLATFORM_CLIENT_MESSAGE
        await db.commit()
        await db.refresh(distribution)

        logger.warning(f"Distribution execute attempted but no platform client exists: {distribution_id}")
        result = model_to_dict(distribution)
        result["error"] = _NO_PLATFORM_CLIENT_MESSAGE
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute distribution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{distribution_id}")
async def get_distribution(
    distribution_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get distribution details"""
    try:
        logger.info(f"Getting distribution {distribution_id}")

        distribution = await db.get(Distribution, uuid.UUID(distribution_id))
        if distribution is None:
            raise HTTPException(status_code=404, detail=f"Distribution not found: {distribution_id}")

        return model_to_dict(distribution)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get distribution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_distributions(
    content_id: Optional[str] = None,
    platform: Optional[str] = None,
    status: Optional[DistributionStatus] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List distributions"""
    try:
        logger.info("Listing distributions")

        query = select(Distribution)
        if content_id is not None:
            query = query.where(Distribution.content_id == uuid.UUID(content_id))
        if platform is not None:
            query = query.where(Distribution.platform == platform)
        if status is not None:
            query = query.where(Distribution.status == status)

        count_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()

        query = query.order_by(Distribution.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(query)
        distributions = [model_to_dict(d) for d in result.scalars().all()]

        return {
            "total": total,
            "distributions": distributions,
            "pagination": {"limit": limit, "offset": offset}
        }

    except Exception as e:
        logger.error(f"Failed to list distributions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
