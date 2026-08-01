"""
SEO router
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from loguru import logger

from app.database import get_db
from app.models.content import Content
from app.models.seo import SEOAnalysis, Keyword
from app.services.seo_analyzer import analyze
from app.utils.serializers import model_to_dict

router = APIRouter()


class AnalyzeRequest(BaseModel):
    """Request to analyze a piece of content for SEO"""
    content_id: str
    primary_keyword: Optional[str] = None
    secondary_keywords: Optional[list] = None


class TrackKeywordRequest(BaseModel):
    """Request to track a keyword"""
    keyword: str
    content_id: Optional[str] = None
    search_volume: Optional[int] = None
    difficulty: Optional[int] = None
    relevance: Optional[int] = None
    target_position: Optional[int] = None


@router.post("/analyze")
async def analyze_content(
    request: AnalyzeRequest,
    db: AsyncSession = Depends(get_db)
):
    """Run a real SEO analysis against a content item's body"""
    try:
        logger.info(f"Analyzing content {request.content_id} for SEO")

        content = await db.get(Content, uuid.UUID(request.content_id))
        if content is None:
            raise HTTPException(status_code=404, detail=f"Content not found: {request.content_id}")
        if not content.body:
            raise HTTPException(status_code=400, detail="Content has no body to analyze yet")

        result = analyze(
            body=content.body,
            title=content.title,
            summary=content.summary,
            primary_keyword=request.primary_keyword,
        )

        analysis = SEOAnalysis(
            content_id=content.id,
            overall_score=result["overall_score"],
            readability_score=result["readability_score"],
            keyword_density_score=result["keyword_density_score"],
            structure_score=result["structure_score"],
            meta_title=result["meta_title"],
            meta_description=result["meta_description"],
            primary_keyword=result["primary_keyword"],
            secondary_keywords=request.secondary_keywords,
            recommendations=result["recommendations"],
        )
        db.add(analysis)

        content.seo_score = result["overall_score"]
        content.keywords = [request.primary_keyword] + (request.secondary_keywords or []) if request.primary_keyword else request.secondary_keywords

        await db.commit()
        await db.refresh(analysis)

        logger.info(f"SEO analysis complete for {request.content_id}: score={result['overall_score']}")
        return model_to_dict(analysis)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to analyze content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{content_id}")
async def get_analysis(
    content_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get the most recent SEO analysis for a content item"""
    try:
        logger.info(f"Getting SEO analysis for {content_id}")

        query = (
            select(SEOAnalysis)
            .where(SEOAnalysis.content_id == uuid.UUID(content_id))
            .order_by(SEOAnalysis.analyzed_at.desc())
        )
        result = await db.execute(query)
        analysis = result.scalars().first()

        if analysis is None:
            raise HTTPException(status_code=404, detail=f"No SEO analysis found for content: {content_id}")

        return model_to_dict(analysis)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get SEO analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/keywords")
async def track_keyword(
    request: TrackKeywordRequest,
    db: AsyncSession = Depends(get_db)
):
    """Track a keyword"""
    try:
        logger.info(f"Tracking keyword: {request.keyword}")

        keyword = Keyword(
            content_id=uuid.UUID(request.content_id) if request.content_id else None,
            keyword=request.keyword,
            search_volume=request.search_volume,
            difficulty=request.difficulty,
            relevance=request.relevance,
            target_position=request.target_position,
        )
        db.add(keyword)
        await db.commit()
        await db.refresh(keyword)

        return model_to_dict(keyword)

    except Exception as e:
        logger.error(f"Failed to track keyword: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keywords/list")
async def list_keywords(
    content_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List tracked keywords"""
    try:
        logger.info("Listing keywords")

        query = select(Keyword)
        if content_id is not None:
            query = query.where(Keyword.content_id == uuid.UUID(content_id))

        count_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()

        query = query.order_by(Keyword.created_at.desc()).limit(limit).offset(offset)
        result = await db.execute(query)
        keywords = [model_to_dict(k) for k in result.scalars().all()]

        return {
            "total": total,
            "keywords": keywords,
            "pagination": {"limit": limit, "offset": offset}
        }

    except Exception as e:
        logger.error(f"Failed to list keywords: {e}")
        raise HTTPException(status_code=500, detail=str(e))
