"""
Distribution router

/publish records a real Distribution row (scheduled or pending).
/{id}/execute attempts the actual post via a real platform client
(WordPress, dev.to) when one exists and is configured; otherwise it
honestly reports status=FAILED with a clear reason (unsupported platform,
missing credentials, or a live error from the platform's API) rather than
faking a successful publish.
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
from app.services.platforms import get_platform_client
from app.utils.serializers import model_to_dict

router = APIRouter()

_UNSUPPORTED_PLATFORM_MESSAGE = "No platform posting client exists for '{platform}'."


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

        content = await db.get(Content, distribution.content_id)

        client = get_platform_client(distribution.platform)
        if client is None:
            distribution.status = DistributionStatus.FAILED
            distribution.error_message = _UNSUPPORTED_PLATFORM_MESSAGE.format(platform=distribution.platform)
        else:
            publish_result = await client.publish(content.title, content.body or "")
            if publish_result.success:
                distribution.status = DistributionStatus.PUBLISHED
                distribution.platform_post_id = publish_result.post_id
                distribution.published_at = datetime.utcnow()
                distribution.error_message = None
            else:
                distribution.status = DistributionStatus.FAILED
                distribution.error_message = publish_result.error
                distribution.retry_count = (distribution.retry_count or 0) + 1

        await db.commit()
        await db.refresh(distribution)

        result = model_to_dict(distribution)
        if distribution.status == DistributionStatus.FAILED:
            logger.warning(f"Distribution execute failed for {distribution_id}: {distribution.error_message}")
            result["error"] = distribution.error_message
        else:
            logger.info(f"Distribution {distribution_id} published to {distribution.platform}: {distribution.platform_post_id}")
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
