from dataclasses import dataclass
from typing import Any, List, Optional


# ── Linked-list Queue (from scratch) ──────────────────────────────────────────

class _Node:
    __slots__ = ("data", "next")

    def __init__(self, data: Any):
        self.data = data
        self.next: Optional["_Node"] = None


class Queue:
    """
    FIFO queue implemented as a singly-linked list.
    enqueue / dequeue / peek are all O(1).
    """

    def __init__(self):
        self._head: Optional[_Node] = None
        self._tail: Optional[_Node] = None
        self._size: int = 0

    def enqueue(self, item: Any) -> None:
        """Add item to the back of the queue. O(1)."""
        node = _Node(item)
        if self._tail is not None:
            self._tail.next = node
        self._tail = node
        if self._head is None:
            self._head = node
        self._size += 1

    def dequeue(self) -> Any:
        """Remove and return the front item. O(1)."""
        if self.is_empty():
            raise IndexError("dequeue from empty queue")
        data = self._head.data
        self._head = self._head.next
        if self._head is None:
            self._tail = None
        self._size -= 1
        return data

    def peek(self) -> Any:
        """Return the front item without removing it. O(1)."""
        if self.is_empty():
            raise IndexError("peek at empty queue")
        return self._head.data

    def is_empty(self) -> bool:
        return self._size == 0

    def size(self) -> int:
        return self._size

    def to_list(self) -> list:
        """Return all items in order (front → back). O(n)."""
        result = []
        node = self._head
        while node is not None:
            result.append(node.data)
            node = node.next
        return result


# ── OrderRouter ────────────────────────────────────────────────────────────────

STATIONS = ["grill", "dessert", "drinks", "sides"]

# Maps menu item category (lowercased) → station name
CATEGORY_MAP: dict = {
    "mains": "grill",
    "grills": "grill",
    "starters": "grill",
    "desserts": "dessert",
    "dessert": "dessert",
    "drinks": "drinks",
    "beverages": "drinks",
    "sides": "sides",
    "side": "sides",
}


@dataclass
class RoutedItem:
    order_id: int
    menu_item_id: int
    name: str
    category: str
    station: str


class OrderRouter:
    """
    Routes order items to per-station queues using category-based mapping.
    Items with unrecognised categories are distributed via round-robin
    across all stations to prevent any one station from backing up.
    """

    def __init__(self):
        self._queues: dict = {s: Queue() for s in STATIONS}
        self._rr_index: int = 0  # round-robin cursor for unmapped categories

    def _station_for(self, category: str) -> str:
        """Return the station for a category, or pick next via round-robin."""
        station = CATEGORY_MAP.get(category.lower())
        if station is None:
            station = STATIONS[self._rr_index % len(STATIONS)]
            self._rr_index += 1
        return station

    def route_order(self, order_id: int, items: List[dict]) -> dict:
        """
        Route each item in the order to the correct station queue.

        Args:
            order_id: DB id of the order.
            items:    list of dicts with keys menu_item_id, name, category.

        Returns:
            {"station": [RoutedItem, ...]} summary of what went where.
        """
        summary: dict = {s: [] for s in STATIONS}
        for item in items:
            station = self._station_for(item.get("category", ""))
            routed = RoutedItem(
                order_id=order_id,
                menu_item_id=item["menu_item_id"],
                name=item["name"],
                category=item["category"],
                station=station,
            )
            self._queues[station].enqueue(routed)
            summary[station].append(routed)
        return summary

    def get_queue(self, station: str) -> List[RoutedItem]:
        """Return all items currently in a station's queue. O(n)."""
        if station not in self._queues:
            return []
        return self._queues[station].to_list()

    def station_sizes(self) -> dict:
        """Return {station: queue_size} for all stations. O(1) per station."""
        return {s: self._queues[s].size() for s in STATIONS}

    def dequeue_from(self, station: str) -> RoutedItem:
        """Remove and return the next item from a station queue. O(1)."""
        if station not in self._queues:
            raise KeyError(f"Unknown station: {station}")
        return self._queues[station].dequeue()

    def available_stations(self) -> List[str]:
        return list(STATIONS)


# Module-level singleton used by the API routes
router_instance = OrderRouter()
