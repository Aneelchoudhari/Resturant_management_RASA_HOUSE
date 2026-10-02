from datetime import datetime, timezone


def compute_priority_score(priority_tier: int, party_size: int, joined_at: datetime) -> float:
    """
    Lower score = higher priority = served first.

    Formula:
      score = (priority_tier * 1000) - wait_seconds - (party_size * 5)

    - priority_tier: 1 is VIP (most urgent), higher numbers are less urgent.
    - wait_seconds: seconds spent in queue; longer wait lowers the score (raises priority).
    - party_size: larger parties get a small priority boost.
    """
    now = datetime.now(timezone.utc)
    if joined_at.tzinfo is None:
        joined_at = joined_at.replace(tzinfo=timezone.utc)
    wait_seconds = (now - joined_at).total_seconds()
    return (priority_tier * 1000) - wait_seconds - (party_size * 5)


class MinHeap:
    """
    Min-heap implemented from scratch.
    Each element is a (score, item_id, item) tuple.
    The element with the lowest score is always at index 0.
    """

    def __init__(self):
        self._data: list = []
        self._positions: dict[int, int] = {}

    # ── index helpers ──────────────────────────────────────────────────────────

    def _parent(self, i: int) -> int:
        return (i - 1) // 2

    def _left(self, i: int) -> int:
        return 2 * i + 1

    def _right(self, i: int) -> int:
        return 2 * i + 2

    def _swap(self, i: int, j: int) -> None:
        self._data[i], self._data[j] = self._data[j], self._data[i]
        self._positions[self._data[i][1]] = i
        self._positions[self._data[j][1]] = j

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
        """Insert or replace the item with this ID. O(log n)."""
        if item_id in self._positions:
            self.update(item_id, score, item)
            return
        self._data.append((score, item_id, item))
        index = len(self._data) - 1
        self._positions[item_id] = index
        self._bubble_up(index)

    def update(self, item_id: int, score: float, item: object) -> None:
        """Update one existing ID, inserting it if absent. O(log n)."""
        index = self._positions.get(item_id)
        if index is None:
            self.push(score, item_id, item)
            return
        old_score = self._data[index][0]
        self._data[index] = (score, item_id, item)
        if score < old_score:
            self._bubble_up(index)
        else:
            self._bubble_down(index)

    def remove(self, item_id: int) -> object | None:
        """Remove an item by ID and return its value, or None if missing."""
        index = self._positions.get(item_id)
        if index is None:
            return None
        self._swap(index, len(self._data) - 1)
        _, removed_id, item = self._data.pop()
        self._positions.pop(removed_id, None)
        if index < len(self._data):
            parent = self._parent(index)
            if index > 0 and self._data[index][0] < self._data[parent][0]:
                self._bubble_up(index)
            else:
                self._bubble_down(index)
        return item

    def heapify(self, entries) -> None:
        """Build from (score, item_id, item) entries in O(n). Last ID wins."""
        by_id = {item_id: (score, item_id, item) for score, item_id, item in entries}
        self._data = list(by_id.values())
        self._positions = {entry[1]: index for index, entry in enumerate(self._data)}
        for index in range(len(self._data) // 2 - 1, -1, -1):
            self._bubble_down(index)

    def pop(self) -> tuple:
        """Remove and return the element with the lowest score. O(log n)."""
        if self.is_empty():
            raise IndexError("pop from empty heap")
        self._swap(0, len(self._data) - 1)
        score, item_id, item = self._data.pop()
        self._positions.pop(item_id, None)
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
        temp.heapify(self._data)
        result = []
        while not temp.is_empty():
            result.append(temp.pop())
        return result
