import pytest
from app.dsa.interval_scheduler import allocate, ReservationSlot, TableSlot, _is_free


# ── helpers ────────────────────────────────────────────────────────────────────

def make_res(rid, start, duration_min, party_size):
    return ReservationSlot(
        reservation_id=rid,
        start=start,
        end=start + duration_min * 60,
        party_size=party_size,
    )


def make_table(tid, capacity):
    return TableSlot(table_id=tid, capacity=capacity)


def assigned_ids(result):
    return {a.reservation_id for a in result["assignments"]}


def table_for(result, reservation_id):
    for a in result["assignments"]:
        if a.reservation_id == reservation_id:
            return a.table_id
    return None


# ── _is_free tests ─────────────────────────────────────────────────────────────

class TestIsFree:
    def test_empty_schedule_is_always_free(self):
        assert _is_free([], 0, 100) is True

    def test_no_overlap_before(self):
        # Existing: [200, 300), new: [0, 100) — no overlap
        assert _is_free([(200, 300)], 0, 100) is True

    def test_no_overlap_after(self):
        # Existing: [0, 100), new: [200, 300) — no overlap
        assert _is_free([(0, 100)], 200, 300) is True

    def test_exact_boundary_touch_allowed(self):
        # Existing ends at 100, new starts at 100 — back-to-back is fine
        assert _is_free([(0, 100)], 100, 200) is True

    def test_overlap_partial_start(self):
        # Existing: [0, 200), new starts at 100 — overlaps
        assert _is_free([(0, 200)], 100, 300) is False

    def test_overlap_partial_end(self):
        # Existing: [100, 300), new ends at 200 — overlaps
        assert _is_free([(100, 300)], 0, 200) is False

    def test_fully_contained_is_overlap(self):
        assert _is_free([(0, 300)], 100, 200) is False

    def test_fully_containing_is_overlap(self):
        assert _is_free([(100, 200)], 0, 300) is False

    def test_multiple_intervals_one_conflicts(self):
        intervals = [(0, 60), (120, 180), (240, 300)]
        # New interval overlaps the second one
        assert _is_free(intervals, 150, 210) is False

    def test_multiple_intervals_none_conflict(self):
        intervals = [(0, 60), (120, 180), (240, 300)]
        assert _is_free(intervals, 180, 240) is True


# ── allocate tests ─────────────────────────────────────────────────────────────

class TestAllocate:
    def test_single_reservation_single_table(self):
        res = [make_res(1, 0, 60, 2)]
        tables = [make_table(10, 4)]
        result = allocate(res, tables)
        assert len(result["assignments"]) == 1
        assert result["assignments"][0].reservation_id == 1
        assert result["assignments"][0].table_id == 10
        assert result["unassigned"] == []

    def test_non_overlapping_reservations_share_table(self):
        # Two reservations that do NOT overlap can share the same table
        res = [make_res(1, 0, 60, 2), make_res(2, 3600, 60, 2)]
        tables = [make_table(10, 4)]
        result = allocate(res, tables)
        assert len(result["assignments"]) == 2
        assert table_for(result, 1) == 10
        assert table_for(result, 2) == 10

    def test_overlapping_reservations_need_separate_tables(self):
        # Both overlap — need two separate tables
        res = [make_res(1, 0, 120, 2), make_res(2, 60, 120, 2)]
        tables = [make_table(10, 4), make_table(11, 4)]
        result = allocate(res, tables)
        assert assigned_ids(result) == {1, 2}
        assert table_for(result, 1) != table_for(result, 2)

    def test_exact_boundary_back_to_back_same_table(self):
        # Res 1 ends at t=3600, Res 2 starts at t=3600 — exact touch, same table OK
        res = [make_res(1, 0, 60, 2), make_res(2, 3600, 60, 2)]
        tables = [make_table(10, 4)]
        result = allocate(res, tables)
        assert len(result["assignments"]) == 2
        assert table_for(result, 1) == table_for(result, 2) == 10

    def test_party_too_large_for_all_tables(self):
        res = [make_res(1, 0, 60, 10)]
        tables = [make_table(10, 4), make_table(11, 6)]
        result = allocate(res, tables)
        assert result["assignments"] == []
        assert result["unassigned"] == [1]

    def test_party_exactly_matches_capacity(self):
        res = [make_res(1, 0, 60, 4)]
        tables = [make_table(10, 4)]
        result = allocate(res, tables)
        assert len(result["assignments"]) == 1

    def test_best_fit_picks_smallest_sufficient_table(self):
        # Tables: capacity 4 and 8. Party size 3 — should pick table with cap 4 (best fit)
        res = [make_res(1, 0, 60, 3)]
        tables = [make_table(10, 4), make_table(11, 8)]
        result = allocate(res, tables)
        assert table_for(result, 1) == 10  # smaller fit chosen

    def test_all_tables_full_returns_unassigned(self):
        # Two overlapping reservations, only one table
        res = [make_res(1, 0, 120, 2), make_res(2, 60, 120, 2)]
        tables = [make_table(10, 4)]
        result = allocate(res, tables)
        assert len(result["assignments"]) == 1
        assert len(result["unassigned"]) == 1

    def test_sorted_by_start_time(self):
        # Deliberately pass reservations out of order; both should still be assigned
        res = [make_res(2, 7200, 60, 2), make_res(1, 0, 60, 2)]
        tables = [make_table(10, 4)]
        result = allocate(res, tables)
        assert assigned_ids(result) == {1, 2}

    def test_empty_reservations(self):
        tables = [make_table(10, 4)]
        result = allocate([], tables)
        assert result["assignments"] == []
        assert result["unassigned"] == []

    def test_empty_tables(self):
        res = [make_res(1, 0, 60, 2)]
        result = allocate(res, [])
        assert result["assignments"] == []
        assert result["unassigned"] == [1]

    def test_multiple_reservations_optimal_packing(self):
        # 3 reservations: R1 and R2 overlap, R3 fits back-to-back after R1
        # Expected: R1→T1, R2→T2, R3→T1 (reuses T1)
        t = 0
        hour = 3600
        res = [
            make_res(1, t, 60, 2),           # [0, 3600)
            make_res(2, t + 30 * 60, 60, 2), # [1800, 5400) — overlaps R1
            make_res(3, t + hour, 60, 2),    # [3600, 7200) — back-to-back with R1
        ]
        tables = [make_table(10, 4), make_table(11, 4)]
        result = allocate(res, tables)
        assert assigned_ids(result) == {1, 2, 3}
        # R1 and R3 can share a table (back-to-back), R2 must be on a different table
        assert table_for(result, 1) != table_for(result, 2)

    def test_no_capacity_match_mixed(self):
        # One reservation fits, one is too large
        res = [make_res(1, 0, 60, 2), make_res(2, 0, 60, 20)]
        tables = [make_table(10, 4)]
        result = allocate(res, tables)
        assert 1 in assigned_ids(result)
        assert 2 in result["unassigned"]
