from datetime import datetime


def compute_priority_score(priority_tier: int, party_size: int, joined_at: datetime) -> float:
    """
    Lower score = higher priority = served first.

    Formula:
      score = (priority_tier * 1000) - wait_seconds - (party_size * 5)

    - priority_tier: 1 is VIP (most urgent), higher numbers are less urgent.
    - wait_seconds: seconds spent in queue; longer wait lowers the score (raises priority).
    - party_size: larger parties get a small priority boost.
    """
    wait_seconds = (datetime.utcnow() - joined_at).total_seconds()
    return (priority_tier * 1000) - wait_seconds - (party_size * 5)


class MinHeap:
    """
    Min-heap implemented from scratch.
    Each element is a (score, item_id, item) tuple.
    The element with the lowest score is always at index 0.
    """

    def __init__(self):
        self._data: list = []

    # ── index helpers ──────────────────────────────────────────────────────────

    def _parent(self, i: int) -> int:
        return (i - 1) // 2

    def _left(self, i: int) -> int:
        return 2 * i + 1

    def _right(self, i: int) -> int:
        return 2 * i + 2

    def _swap(self, i: int, j: int) -> None:
        self._data[i], self._data[j] = self._data[j], self._data[i]

    # ── core heap operations ───────────────────────────────────────────────────

    def _bubble_up(self, i: int) -> None:
        """Move element at index i upward until the heap property is restored."""
        while i > 0:
            p = self._parent(i)
            if self._data[i][0] < self._data[p][0]:
                self._swap(i, p)
                i = p
            else:
                break

    def _bubble_down(self, i: int) -> None:
        """Move element at index i downward until the heap property is restored."""
        n = len(self._data)
        while True:
            smallest = i
            left = self._left(i)
            right = self._right(i)
            if left < n and self._data[left][0] < self._data[smallest][0]:
                smallest = left
            if right < n and self._data[right][0] < self._data[smallest][0]:
                smallest = right
            if smallest != i:
                self._swap(i, smallest)
                i = smallest
            else:
                break

    # ── public API ─────────────────────────────────────────────────────────────

    def push(self, score: float, item_id: int, item: object) -> None:
        """Insert (score, item_id, item) into the heap. O(log n)."""
        self._data.append((score, item_id, item))
        self._bubble_up(len(self._data) - 1)

    def pop(self) -> tuple:
        """Remove and return the element with the lowest score. O(log n)."""
        if self.is_empty():
            raise IndexError("pop from empty heap")
        self._swap(0, len(self._data) - 1)
        score, item_id, item = self._data.pop()
        if self._data:
            self._bubble_down(0)
        return score, item_id, item

    def peek(self) -> tuple:
        """Return the element with the lowest score without removing it. O(1)."""
        if self.is_empty():
            raise IndexError("peek at empty heap")
        return self._data[0]

    def size(self) -> int:
        return len(self._data)

    def is_empty(self) -> bool:
        return len(self._data) == 0

    def to_sorted_list(self) -> list:
        """
        Return all elements in ascending score order without modifying this heap.
        Builds a temporary copy and pops from it — O(n log n).
        """
        temp = MinHeap()
        temp._data = list(self._data)
        result = []
        while not temp.is_empty():
            result.append(temp.pop())
        return result
