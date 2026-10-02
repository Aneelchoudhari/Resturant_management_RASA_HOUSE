from dataclasses import dataclass
from bisect import bisect_left
from typing import List


@dataclass
class ReservationSlot:
    reservation_id: int
    start: float   # unix timestamp (seconds)
    end: float     # start + duration_seconds
    party_size: int


@dataclass
class TableSlot:
    table_id: int
    capacity: int


@dataclass
class Assignment:
    reservation_id: int
    table_id: int


def _is_free(intervals: list, start: float, end: float) -> bool:
    """Check overlap in a start-sorted, non-overlapping interval list in O(log k).

    Exact boundary touch is allowed; intervals are half-open [start, end).
    """
    return _free_position(intervals, start, end) is not None


def _free_position(intervals: list, start: float, end: float) -> int | None:
    """Find a valid insertion point in a start-sorted, non-overlapping schedule."""
    position = bisect_left(intervals, (start, float("-inf")))
    if position and intervals[position - 1][1] > start:
        return None
    if position < len(intervals) and intervals[position][0] < end:
        return None
    return position


def allocate(
    reservations: List[ReservationSlot],
    tables: List[TableSlot],
    existing_assignments: dict[int, list[tuple[float, float]]] | None = None,
) -> dict:
    """
    Greedy interval scheduler: start-time order, best-fit capacity, first-free table.

    Sort reservations by start and tables by capacity once. For each reservation,
    scan tables in best-fit order and use binary search to test its sorted interval
    list. The first suitable free table is selected. Boundary-touching bookings
    remain allowed. List insertion can still be O(k) when a new interval falls
    before existing intervals; common chronological appends are O(1). With R
    reservations and T tables, worst-case work is O(R log R + T log T + R*T*log R
    + R^2) due to candidate scans and list insertion; typical chronological plans
    avoid the full interval scan and append costs.

    Args:
        reservations: list of ReservationSlot (id, start, end, party_size)
        tables:       list of TableSlot (id, capacity)

    Returns:
        {
            "assignments": [Assignment(reservation_id, table_id), ...],
            "unassigned":  [reservation_id, ...]
        }
    """
    if not reservations or not tables:
        return {"assignments": [], "unassigned": [r.reservation_id for r in reservations]}

    sorted_reservations = sorted(reservations, key=lambda r: r.start)
    sorted_tables = sorted(tables, key=lambda t: t.capacity)
    capacities = [table.capacity for table in sorted_tables]

    # table_id -> list of (start, end) booked intervals
    existing_assignments = existing_assignments or {}
    schedule: dict = {
        table.table_id: sorted(existing_assignments.get(table.table_id, []))
        for table in sorted_tables
    }

    assignments: List[Assignment] = []
    unassigned: List[int] = []

    for res in sorted_reservations:
        # Best-fit: smallest table that still fits the party
        first_eligible = bisect_left(capacities, res.party_size)

        placed = False
        for table_index in range(first_eligible, len(sorted_tables)):
            table = sorted_tables[table_index]
            position = _free_position(schedule[table.table_id], res.start, res.end)
            if position is not None:
                schedule[table.table_id].insert(position, (res.start, res.end))
                assignments.append(Assignment(reservation_id=res.reservation_id, table_id=table.table_id))
                placed = True
                break

        if not placed:
            unassigned.append(res.reservation_id)

    return {"assignments": assignments, "unassigned": unassigned}
