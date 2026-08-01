"""
Calendar router
"""

import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from loguru import logger

from app.database import get_db
from app.models.calendar import CalendarEntry
from app.utils.serializers import model_to_dict

router = APIRouter()


class ScheduleEntryRequest(BaseModel):
    """Request to schedule a calendar entry"""
    title: str
    description: Optional[str] = None
    scheduled_date: datetime
    scheduled_time: Optional[str] = None
    platforms: List[str]
    content_id: Optional[str] = None


class UpdateEntryRequest(BaseModel):
    """Request to update a calendar entry"""
    title: Optional[str] = None
    scheduled_date: Optional[datetime] = None
    scheduled_time: Optional[str] = None
    platforms: Optional[List[str]] = None
    status: Optional[str] = None


@router.post("/schedule")
async def schedule_entry(
    request: ScheduleEntryRequest,
    db: AsyncSession = Depends(get_db)
):
    """Schedule a calendar entry"""
    try:
        logger.info(f"Scheduling calendar entry: {request.title}")

        entry = CalendarEntry(
            title=request.title,
            description=request.description,
            scheduled_date=request.scheduled_date,
            scheduled_time=request.scheduled_time,
            platforms=request.platforms,
            content_id=uuid.UUID(request.content_id) if request.content_id else None,
            status="scheduled",
        )
        db.add(entry)
        await db.commit()
        await db.refresh(entry)

        return model_to_dict(entry)

    except Exception as e:
        logger.error(f"Failed to schedule entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entry_id}")
async def get_entry(
    entry_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a calendar entry"""
    try:
        logger.info(f"Getting calendar entry {entry_id}")

        entry = await db.get(CalendarEntry, uuid.UUID(entry_id))
        if entry is None:
            raise HTTPException(status_code=404, detail=f"Calendar entry not found: {entry_id}")

        return model_to_dict(entry)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get calendar entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_entries(
    status: Optional[str] = None,
    starts_after: Optional[datetime] = None,
    starts_before: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List calendar entries"""
    try:
        logger.info("Listing calendar entries")

        query = select(CalendarEntry)
        if status is not None:
            query = query.where(CalendarEntry.status == status)
        if starts_after is not None:
            query = query.where(CalendarEntry.scheduled_date >= starts_after)
        if starts_before is not None:
            query = query.where(CalendarEntry.scheduled_date <= starts_before)

        count_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar_one()

        query = query.order_by(CalendarEntry.scheduled_date.asc()).limit(limit).offset(offset)
        result = await db.execute(query)
        entries = [model_to_dict(e) for e in result.scalars().all()]

        return {
            "total": total,
            "entries": entries,
            "pagination": {"limit": limit, "offset": offset}
        }

    except Exception as e:
        logger.error(f"Failed to list calendar entries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{entry_id}")
async def update_entry(
    entry_id: str,
    request: UpdateEntryRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update a calendar entry"""
    try:
        logger.info(f"Updating calendar entry {entry_id}")

        entry = await db.get(CalendarEntry, uuid.UUID(entry_id))
        if entry is None:
            raise HTTPException(status_code=404, detail=f"Calendar entry not found: {entry_id}")

        for field, value in request.model_dump(exclude_unset=True).items():
            setattr(entry, field, value)

        await db.commit()
        await db.refresh(entry)

        return model_to_dict(entry)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update calendar entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{entry_id}/skip")
async def skip_entry(
    entry_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Skip a scheduled calendar entry"""
    try:
        logger.info(f"Skipping calendar entry {entry_id}")

        entry = await db.get(CalendarEntry, uuid.UUID(entry_id))
        if entry is None:
            raise HTTPException(status_code=404, detail=f"Calendar entry not found: {entry_id}")

        entry.status = "skipped"
        await db.commit()
        await db.refresh(entry)

        return model_to_dict(entry)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to skip calendar entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{entry_id}")
async def delete_entry(
    entry_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a calendar entry"""
    try:
        logger.info(f"Deleting calendar entry {entry_id}")

        entry = await db.get(CalendarEntry, uuid.UUID(entry_id))
        if entry is None:
            raise HTTPException(status_code=404, detail=f"Calendar entry not found: {entry_id}")

        await db.delete(entry)
        await db.commit()

        return {"id": entry_id, "deleted": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete calendar entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))
