from dataclasses import dataclass
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
    """
    Return True if [start, end) does not overlap any interval in the list.
    Two intervals overlap when NOT (end <= other_start OR start >= other_end).
    Exact boundary touch (end == other_start) is allowed — back-to-back bookings are fine.
    """
    for s, e in intervals:
        if not (end <= s or start >= e):
            return False
    return True


def allocate(
    reservations: List[ReservationSlot],
    tables: List[TableSlot],
) -> dict:
    """
    Greedy interval-scheduling allocator.

    Algorithm  — O(n log n):
      1. Sort reservations by start time.
      2. For each reservation in that order, scan eligible tables (capacity >= party_size)
         sorted by capacity ascending (best-fit: wastes the least seats).
      3. Assign the first eligible table that is free during [start, end).
      4. If no table is free/large enough, add to unassigned list.

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

    # table_id -> list of (start, end) booked intervals
    schedule: dict = {t.table_id: [] for t in tables}

    assignments: List[Assignment] = []
    unassigned: List[int] = []

    for res in sorted_reservations:
        # Best-fit: smallest table that still fits the party
        eligible = sorted(
            [t for t in tables if t.capacity >= res.party_size],
            key=lambda t: t.capacity,
        )

        placed = False
        for table in eligible:
            if _is_free(schedule[table.table_id], res.start, res.end):
                schedule[table.table_id].append((res.start, res.end))
                assignments.append(Assignment(reservation_id=res.reservation_id, table_id=table.table_id))
                placed = True
                break

        if not placed:
            unassigned.append(res.reservation_id)

    return {"assignments": assignments, "unassigned": unassigned}
