import pytest
import random
from datetime import datetime, timedelta
from app.dsa.priority_queue import MinHeap, compute_priority_score


# ── MinHeap unit tests ─────────────────────────────────────────────────────────

class TestMinHeapPushPop:
    def test_single_element_push_pop(self):
        heap = MinHeap()
        heap.push(42, 1, "only")
        score, item_id, item = heap.pop()
        assert score == 42
        assert item == "only"
        assert heap.is_empty()

    def test_pop_returns_minimum_score_first(self):
        heap = MinHeap()
        heap.push(10, 1, "a")
        heap.push(5, 2, "b")
        heap.push(15, 3, "c")
        heap.push(1, 4, "d")

        score, _, item = heap.pop()
        assert score == 1
        assert item == "d"

        score, _, item = heap.pop()
        assert score == 5
        assert item == "b"

    def test_pop_full_sorted_order(self):
        heap = MinHeap()
        scores = [7, 3, 9, 1, 5]
        for i, s in enumerate(scores):
            heap.push(s, i, f"item_{s}")

        extracted = []
        while not heap.is_empty():
            score, _, _ = heap.pop()
            extracted.append(score)

        assert extracted == sorted(scores)

    def test_pop_from_empty_raises_index_error(self):
        heap = MinHeap()
        with pytest.raises(IndexError):
            heap.pop()

    def test_peek_does_not_remove(self):
        heap = MinHeap()
        heap.push(5, 1, "x")
        heap.push(2, 2, "y")
        score, _, _ = heap.peek()
        assert score == 2
        assert heap.size() == 2

    def test_peek_on_empty_raises_index_error(self):
        heap = MinHeap()
        with pytest.raises(IndexError):
            heap.peek()

    def test_size_tracks_correctly(self):
        heap = MinHeap()
        assert heap.size() == 0
        heap.push(1, 1, "a")
        assert heap.size() == 1
        heap.push(2, 2, "b")
        assert heap.size() == 2
        heap.pop()
        assert heap.size() == 1

    def test_is_empty(self):
        heap = MinHeap()
        assert heap.is_empty()
        heap.push(1, 1, "a")
        assert not heap.is_empty()
        heap.pop()
        assert heap.is_empty()

    def test_negative_scores(self):
        heap = MinHeap()
        heap.push(-10, 1, "a")
        heap.push(-5, 2, "b")
        heap.push(-20, 3, "c")

        score, _, item = heap.pop()
        assert score == -20
        assert item == "c"

    def test_equal_scores_all_items_returned(self):
        heap = MinHeap()
        heap.push(5, 1, "first")
        heap.push(5, 2, "second")
        heap.push(5, 3, "third")

        items = [heap.pop() for _ in range(3)]
        assert len(items) == 3
        assert all(s == 5 for s, _, _ in items)
        assert heap.is_empty()

    def test_large_heap_sorted_order(self):
        heap = MinHeap()
        values = random.sample(range(1000), 100)
        for i, v in enumerate(values):
            heap.push(v, i, f"item_{v}")

        extracted = []
        while not heap.is_empty():
            score, _, _ = heap.pop()
            extracted.append(score)

        assert extracted == sorted(values)

    def test_float_scores(self):
        heap = MinHeap()
        heap.push(1.5, 1, "a")
        heap.push(1.1, 2, "b")
        heap.push(1.9, 3, "c")

        score, _, _ = heap.pop()
        assert score == pytest.approx(1.1)


class TestToSortedList:
    def test_returns_sorted_order(self):
        heap = MinHeap()
        heap.push(3, 1, "a")
        heap.push(1, 2, "b")
        heap.push(2, 3, "c")

        result = heap.to_sorted_list()
        assert [s for s, _, _ in result] == [1, 2, 3]

    def test_does_not_modify_original_heap(self):
        heap = MinHeap()
        heap.push(3, 1, "a")
        heap.push(1, 2, "b")
        heap.push(2, 3, "c")

        heap.to_sorted_list()

        assert heap.size() == 3
        score, _, _ = heap.peek()
        assert score == 1

    def test_empty_heap_returns_empty_list(self):
        heap = MinHeap()
        assert heap.to_sorted_list() == []

    def test_single_element(self):
        heap = MinHeap()
        heap.push(7, 1, "only")
        result = heap.to_sorted_list()
        assert len(result) == 1
        assert result[0][0] == 7


# ── compute_priority_score tests ───────────────────────────────────────────────

class TestPriorityScore:
    def test_lower_tier_has_lower_score(self):
        now = datetime.utcnow()
        score_tier1 = compute_priority_score(1, 2, now)
        score_tier2 = compute_priority_score(2, 2, now)
        score_tier3 = compute_priority_score(3, 2, now)
        assert score_tier1 < score_tier2 < score_tier3

    def test_longer_wait_lowers_score(self):
        now = datetime.utcnow()
        joined_5min_ago = now - timedelta(minutes=5)
        joined_10min_ago = now - timedelta(minutes=10)

        score_new = compute_priority_score(1, 2, now)
        score_5min = compute_priority_score(1, 2, joined_5min_ago)
        score_10min = compute_priority_score(1, 2, joined_10min_ago)

        assert score_10min < score_5min < score_new

    def test_larger_party_lowers_score(self):
        now = datetime.utcnow()
        score_small = compute_priority_score(1, 1, now)
        score_large = compute_priority_score(1, 8, now)
        assert score_large < score_small

    def test_wait_time_can_overcome_tier_difference(self):
        now = datetime.utcnow()
        # Tier 2 guest who has waited 20 minutes vs tier 3 guest who just arrived
        tier2_long_wait = compute_priority_score(2, 2, now - timedelta(minutes=20))
        tier3_just_joined = compute_priority_score(3, 2, now)
        # Tier 2 long-wait should have lower score than tier 3 who just joined
        # (2*1000 - 1200 - 10) = 790  vs  (3*1000 - 0 - 10) = 2990
        assert tier2_long_wait < tier3_just_joined
