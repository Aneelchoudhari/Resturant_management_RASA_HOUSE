from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from app.database import get_db
from app import models
from app.dsa.table_graph import Graph
from app.auth import require_roles

router = APIRouter(prefix="/tables", tags=["tables"])

# Only admin and manager can configure table adjacency
ADJACENCY_MANAGEMENT_ROLES = (
    models.StaffRole.admin,
    models.StaffRole.manager,
)

# Any staff can query combine results (read-only)
FLOOR_VIEW_ROLES = (
    models.StaffRole.admin,
    models.StaffRole.manager,
    models.StaffRole.waiter,
    models.StaffRole.receptionist,
)


# ── response schemas ───────────────────────────────────────────────────────────

class TableGroupResponse(BaseModel):
    table_ids: List[int]
    table_numbers: List[int]
    total_capacity: int
    can_seat_party: bool


class CombineResponse(BaseModel):
    party_size: int
    viable_groups: List[TableGroupResponse]


class AdjacencyResponse(BaseModel):
    table_id: int
    adjacent_table_ids: List[int]


# ── adjacency management ───────────────────────────────────────────────────────

@router.post("/{table_id}/adjacent/{other_id}", response_model=AdjacencyResponse, status_code=201)
def add_adjacency(
    table_id: int,
    other_id: int,
    db: Session = Depends(get_db),
    _: models.Staff = Depends(require_roles(*ADJACENCY_MANAGEMENT_ROLES)),
):
    """Persist a physical adjacency edge — admin/manager only."""
    if table_id == other_id:
        raise HTTPException(status_code=422, detail="A table cannot be adjacent to itself")
    for tid in (table_id, other_id):
        if not db.query(models.Table).filter(models.Table.id == tid).first():
            raise HTTPException(status_code=404, detail=f"Table id={tid} not found")
    low_id, high_id = sorted((table_id, other_id))
    edge = db.query(models.TableAdjacency).filter_by(
        table_id_low=low_id,
        table_id_high=high_id,
    ).first()
    if edge is None:
        db.add(models.TableAdjacency(table_id_low=low_id, table_id_high=high_id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            edge = db.query(models.TableAdjacency).filter_by(
                table_id_low=low_id,
                table_id_high=high_id,
            ).first()
            if edge is None:
                raise
    neighbors = _neighbors(db, table_id)
    return AdjacencyResponse(
        table_id=table_id,
        adjacent_table_ids=neighbors,
    )


def _neighbors(db: Session, table_id: int) -> List[int]:
    edges = db.query(models.TableAdjacency).filter(
        or_(
            models.TableAdjacency.table_id_low == table_id,
            models.TableAdjacency.table_id_high == table_id,
        )
    ).all()
    return sorted(
        edge.table_id_high if edge.table_id_low == table_id else edge.table_id_low
        for edge in edges
    )


@router.delete("/{table_id}/adjacent/{other_id}", status_code=204)
def remove_adjacency(
    table_id: int,
    other_id: int,
    db: Session = Depends(get_db),
    _: models.Staff = Depends(require_roles(*ADJACENCY_MANAGEMENT_ROLES)),
):
    """Remove the persisted adjacency edge — admin/manager only."""
    low_id, high_id = sorted((table_id, other_id))
    db.query(models.TableAdjacency).filter_by(
        table_id_low=low_id,
        table_id_high=high_id,
    ).delete(synchronize_session=False)
    db.commit()


# ── GET /tables/combine ────────────────────────────────────────────────────────

@router.get("/combine", response_model=CombineResponse)
def combine_tables(
    party_size: int,
    db: Session = Depends(get_db),
    _: models.Staff = Depends(require_roles(*FLOOR_VIEW_ROLES)),
):
    """
    Use BFS to find all connected table groups that can seat a party.
    Restricted to staff with floor access (admin, manager, waiter, host).
    """
    tables = db.query(models.Table).all()
    table_map = {t.id: t for t in tables}

    graph = Graph()
    for t in tables:
        graph.add_node(t.id)

    table_ids = set(table_map)
    edges = db.query(models.TableAdjacency).all()
    for edge in edges:
        if edge.table_id_low in table_ids and edge.table_id_high in table_ids:
            graph.add_edge(edge.table_id_low, edge.table_id_high)

    components = graph.connected_components()

    groups: List[TableGroupResponse] = []
    for component in components:
        db_tables = [table_map[tid] for tid in component if tid in table_map]
        if not db_tables:
            continue
        total_capacity = sum(t.capacity for t in db_tables)
        groups.append(
            TableGroupResponse(
                table_ids=[t.id for t in db_tables],
                table_numbers=[t.number for t in db_tables],
                total_capacity=total_capacity,
                can_seat_party=total_capacity >= party_size,
            )
        )

    # Sort: viable groups first, then by total capacity descending
    groups.sort(key=lambda g: (not g.can_seat_party, -g.total_capacity))

    return CombineResponse(party_size=party_size, viable_groups=groups)
