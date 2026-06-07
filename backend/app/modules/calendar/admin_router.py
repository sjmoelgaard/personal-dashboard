from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_auth
from app.core.database import get_db
from app.modules.calendar.source_models import CalendarSource
from app.modules.calendar.source_schemas import CalendarSourceCreate, CalendarSourceOut
from app.modules.calendar.service import sync_source

router = APIRouter()


@router.get("/calendar-sources", response_model=list[CalendarSourceOut])
async def list_sources(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
):
    result = await db.execute(
        select(CalendarSource).order_by(CalendarSource.created_at)
    )
    return list(result.scalars().all())


@router.post("/calendar-sources", response_model=CalendarSourceOut, status_code=201)
async def create_source(
    body: CalendarSourceCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
):
    source = CalendarSource(**body.model_dump())
    db.add(source)
    await db.commit()
    await db.refresh(source)
    # Sync straks — fejl her fejler ikke create
    try:
        await sync_source(db, source.id)
    except Exception:
        pass
    return source


@router.delete("/calendar-sources/{source_id}", status_code=204)
async def delete_source(
    source_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_auth),
):
    result = await db.execute(
        select(CalendarSource).where(CalendarSource.id == source_id)
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kilde ikke fundet")
    await db.delete(source)
    await db.commit()
