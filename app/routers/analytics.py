"""
Analytics router

Real aggregation over Content and Distribution data - no separate analytics
table needed, and no fabricated numbers.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from loguru import logger

from app.database import get_db
from app.models.content import Content, ContentStatus, ContentType
from app.models.distribution import Distribution, DistributionStatus

router = APIRouter()


class TrackEventRequest(BaseModel):
    """Request to record a real usage event against a content item"""
    views: int = 0
    engagements: int = 0
    conversions: int = 0


@router.get("/overview")
async def get_overview(
    db: AsyncSession = Depends(get_db)
):
    """Fleet-wide content performance overview"""
    try:
        logger.info("Building analytics overview")

        totals = (await db.execute(
            select(
                func.count(Content.id),
                func.coalesce(func.sum(Content.views), 0),
                func.coalesce(func.sum(Content.engagements), 0),
                func.coalesce(func.sum(Content.conversions), 0),
                func.coalesce(func.avg(Content.seo_score), 0),
            )
        )).one()
        total_content, total_views, total_engagements, total_conversions, avg_seo_score = totals

        by_status_rows = (await db.execute(
            select(Content.status, func.count(Content.id)).group_by(Content.status)
        )).all()
        by_status = {status.value: count for status, count in by_status_rows}

        by_type_rows = (await db.execute(
            select(Content.content_type, func.count(Content.id)).group_by(Content.content_type)
        )).all()
        by_type = {content_type.value: count for content_type, count in by_type_rows}

        by_platform_rows = (await db.execute(
            select(Distribution.platform, Distribution.status, func.count(Distribution.id))
            .group_by(Distribution.platform, Distribution.status)
        )).all()
        by_platform: dict = {}
        for platform, status, count in by_platform_rows:
            by_platform.setdefault(platform, {})[status.value] = count

        return {
            "total_content": total_content,
            "total_views": int(total_views),
            "total_engagements": int(total_engagements),
            "total_conversions": int(total_conversions),
            "average_seo_score": round(float(avg_seo_score), 1),
            "content_by_status": by_status,
            "content_by_type": by_type,
            "distributions_by_platform": by_platform,
        }

    except Exception as e:
        logger.error(f"Failed to build analytics overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/content/{content_id}/performance")
async def get_content_performance(
    content_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Performance for a single content item, including its real distributions"""
    try:
        logger.info(f"Getting performance for content {content_id}")

        content = await db.get(Content, uuid.UUID(content_id))
        if content is None:
            raise HTTPException(status_code=404, detail=f"Content not found: {content_id}")

        dist_result = await db.execute(
            select(Distribution).where(Distribution.content_id == content.id)
        )
        distributions = dist_result.scalars().all()

        conversion_rate = (content.conversions / content.views * 100) if content.views else 0.0

        return {
            "content_id": content_id,
            "title": content.title,
            "status": content.status.value,
            "seo_score": content.seo_score,
            "views": content.views,
            "engagements": content.engagements,
            "conversions": content.conversions,
            "conversion_rate_percent": round(conversion_rate, 2),
            "distributions": [
                {
                    "platform": d.platform,
                    "status": d.status.value,
                    "views": d.views,
                    "likes": d.likes,
                    "shares": d.shares,
                    "comments": d.comments,
                }
                for d in distributions
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get content performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/content/{content_id}/track")
async def track_content_event(
    content_id: str,
    request: TrackEventRequest,
    db: AsyncSession = Depends(get_db)
):
    """Record real view/engagement/conversion counts against a content item"""
    try:
        logger.info(f"Tracking event for content {content_id}")

        content = await db.get(Content, uuid.UUID(content_id))
        if content is None:
            raise HTTPException(status_code=404, detail=f"Content not found: {content_id}")

        content.views += request.views
        content.engagements += request.engagements
        content.conversions += request.conversions
        await db.commit()
        await db.refresh(content)

        return {
            "content_id": content_id,
            "views": content.views,
            "engagements": content.engagements,
            "conversions": content.conversions,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to track content event: {e}")
        raise HTTPException(status_code=500, detail=str(e))
