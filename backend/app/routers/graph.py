from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from app.database import get_db
from app import models
from app.dsa.table_graph import Graph

router = APIRouter(prefix="/tables", tags=["tables"])

# Module-level graph singleton — persists adjacency between requests
graph_instance = Graph()


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
def add_adjacency(table_id: int, other_id: int, db: Session = Depends(get_db)):
    """Mark two tables as physically adjacent (combinable)."""
    for tid in (table_id, other_id):
        if not db.query(models.Table).filter(models.Table.id == tid).first():
            raise HTTPException(status_code=404, detail=f"Table id={tid} not found")
    graph_instance.add_edge(table_id, other_id)
    return AdjacencyResponse(
        table_id=table_id,
        adjacent_table_ids=graph_instance.neighbors(table_id),
    )


@router.delete("/{table_id}/adjacent/{other_id}", status_code=204)
def remove_adjacency(table_id: int, other_id: int):
    """Remove the adjacency edge between two tables."""
    graph_instance.remove_edge(table_id, other_id)


# ── GET /tables/combine ────────────────────────────────────────────────────────

@router.get("/combine", response_model=CombineResponse)
def combine_tables(party_size: int, db: Session = Depends(get_db)):
    """
    Use BFS to find all connected table groups that can seat a party.

    Algorithm  — O(V + E):
      1. Ensure every table in the DB is a node in the graph.
      2. Find all connected components via BFS.
      3. For each component, sum capacities and flag those >= party_size.
    """
    tables = db.query(models.Table).all()
    table_map = {t.id: t for t in tables}

    # Sync DB tables into graph (no-op if already added)
    for t in tables:
        graph_instance.add_node(t.id)

    components = graph_instance.connected_components()

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
