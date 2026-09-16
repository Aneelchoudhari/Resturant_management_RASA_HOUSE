from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from app.database import get_db
from app import models, schemas
from app.dsa.priority_queue import MinHeap, compute_priority_score

router = APIRouter(prefix="/waitlist", tags=["waitlist"])


# ── response schemas (local, specific to this module) ─────────────────────────

class WaitlistPositionResponse(BaseModel):
    position: int
    entry: schemas.WaitlistEntryResponse


class WaitlistQueueItem(BaseModel):
    position: int
    score: float
    entry: schemas.WaitlistEntryResponse


# ── helpers ────────────────────────────────────────────────────────────────────

def _build_heap(db: Session) -> MinHeap:
    """Load all waitlist entries from DB and build a fresh min-heap."""
    entries = db.query(models.WaitlistEntry).all()
    heap = MinHeap()
    for e in entries:
        score = compute_priority_score(e.priority_tier, e.party_size, e.joined_at)
        heap.push(score, e.id, schemas.WaitlistEntryResponse.model_validate(e))
    return heap


# ── routes ─────────────────────────────────────────────────────────────────────

@router.post("/join", response_model=WaitlistPositionResponse, status_code=201)
def join_waitlist(payload: schemas.WaitlistEntryCreate, db: Session = Depends(get_db)):
    entry = models.WaitlistEntry(
        guest_name=payload.guest_name,
        party_size=payload.party_size,
        priority_tier=payload.priority_tier,
        joined_at=datetime.utcnow(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    heap = _build_heap(db)
    sorted_entries = heap.to_sorted_list()
    position = next(
        (i + 1 for i, (_, eid, _) in enumerate(sorted_entries) if eid == entry.id),
        heap.size(),
    )
    return WaitlistPositionResponse(
        position=position,
        entry=schemas.WaitlistEntryResponse.model_validate(entry),
    )


@router.get("/", response_model=List[WaitlistQueueItem])
def get_waitlist(db: Session = Depends(get_db)):
    heap = _build_heap(db)
    sorted_entries = heap.to_sorted_list()
    return [
        WaitlistQueueItem(position=i + 1, score=round(score, 2), entry=entry_data)
        for i, (score, _, entry_data) in enumerate(sorted_entries)
    ]
