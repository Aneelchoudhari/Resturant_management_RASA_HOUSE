import pytest
from app.dsa.order_router import Queue, OrderRouter, STATIONS, CATEGORY_MAP


# ── Queue tests ────────────────────────────────────────────────────────────────

class TestQueue:
    def test_enqueue_dequeue_single(self):
        q = Queue()
        q.enqueue("a")
        assert q.dequeue() == "a"

    def test_fifo_order(self):
        q = Queue()
        for item in ["first", "second", "third"]:
            q.enqueue(item)
        assert q.dequeue() == "first"
        assert q.dequeue() == "second"
        assert q.dequeue() == "third"

    def test_dequeue_from_empty_raises(self):
        q = Queue()
        with pytest.raises(IndexError):
            q.dequeue()

    def test_peek_returns_front_without_removing(self):
        q = Queue()
        q.enqueue(42)
        q.enqueue(99)
        assert q.peek() == 42
        assert q.size() == 2

    def test_peek_empty_raises(self):
        q = Queue()
        with pytest.raises(IndexError):
            q.peek()

    def test_is_empty(self):
        q = Queue()
        assert q.is_empty()
        q.enqueue("x")
        assert not q.is_empty()
        q.dequeue()
        assert q.is_empty()

    def test_size_tracks_correctly(self):
        q = Queue()
        assert q.size() == 0
        q.enqueue("a")
        q.enqueue("b")
        assert q.size() == 2
        q.dequeue()
        assert q.size() == 1

    def test_to_list_preserves_order(self):
        q = Queue()
        for i in range(5):
            q.enqueue(i)
        assert q.to_list() == [0, 1, 2, 3, 4]

    def test_to_list_does_not_dequeue(self):
        q = Queue()
        q.enqueue("x")
        q.to_list()
        assert q.size() == 1

    def test_empty_to_list(self):
        q = Queue()
        assert q.to_list() == []

    def test_interleaved_enqueue_dequeue(self):
        q = Queue()
        q.enqueue(1)
        q.enqueue(2)
        assert q.dequeue() == 1
        q.enqueue(3)
        assert q.dequeue() == 2
        assert q.dequeue() == 3
        assert q.is_empty()

    def test_large_queue(self):
        q = Queue()
        for i in range(1000):
            q.enqueue(i)
        assert q.size() == 1000
        for i in range(1000):
            assert q.dequeue() == i
        assert q.is_empty()


# ── OrderRouter tests ──────────────────────────────────────────────────────────

def make_item(menu_item_id, name, category):
    return {"menu_item_id": menu_item_id, "name": name, "category": category}


class TestOrderRouter:
    def setup_method(self):
        """Create a fresh router for each test."""
        self.router = OrderRouter()

    def test_known_category_routes_to_correct_station(self):
        items = [make_item(1, "Burger", "mains")]
        summary = self.router.route_order(order_id=1, items=items)
        assert len(summary["grill"]) == 1
        assert summary["grill"][0].name == "Burger"

    def test_dessert_category_routing(self):
        items = [make_item(1, "Brownie", "desserts")]
        summary = self.router.route_order(order_id=1, items=items)
        assert len(summary["dessert"]) == 1

    def test_drinks_category_routing(self):
        items = [make_item(1, "Cola", "drinks")]
        summary = self.router.route_order(order_id=1, items=items)
        assert len(summary["drinks"]) == 1

    def test_sides_category_routing(self):
        items = [make_item(1, "Fries", "sides")]
        summary = self.router.route_order(order_id=1, items=items)
        assert len(summary["sides"]) == 1

    def test_order_with_multiple_items_split_correctly(self):
        items = [
            make_item(1, "Burger", "mains"),
            make_item(2, "Cola", "drinks"),
            make_item(3, "Brownie", "desserts"),
            make_item(4, "Fries", "sides"),
        ]
        summary = self.router.route_order(order_id=1, items=items)
        assert len(summary["grill"]) == 1
        assert len(summary["drinks"]) == 1
        assert len(summary["dessert"]) == 1
        assert len(summary["sides"]) == 1

    def test_unknown_category_uses_round_robin(self):
        """Unknown categories must be distributed across stations, not pile up on one."""
        items = [make_item(i, f"Mystery{i}", "unknown") for i in range(8)]
        summary = self.router.route_order(order_id=1, items=items)
        total = sum(len(v) for v in summary.values())
        assert total == 8
        # Each station should receive exactly 2 items (8 items / 4 stations)
        for station in STATIONS:
            assert len(summary[station]) == 2

    def test_get_queue_returns_items_in_order(self):
        self.router.route_order(order_id=1, items=[make_item(1, "Steak", "mains")])
        self.router.route_order(order_id=2, items=[make_item(2, "Chicken", "mains")])
        q = self.router.get_queue("grill")
        assert q[0].order_id == 1
        assert q[1].order_id == 2

    def test_get_queue_unknown_station_returns_empty(self):
        assert self.router.get_queue("nonexistent") == []

    def test_station_sizes_all_zero_initially(self):
        sizes = self.router.station_sizes()
        assert all(v == 0 for v in sizes.values())

    def test_station_sizes_update_after_routing(self):
        items = [make_item(1, "Burger", "mains"), make_item(2, "Cola", "drinks")]
        self.router.route_order(order_id=1, items=items)
        sizes = self.router.station_sizes()
        assert sizes["grill"] == 1
        assert sizes["drinks"] == 1

    def test_dequeue_from_station(self):
        self.router.route_order(order_id=1, items=[make_item(1, "Burger", "mains")])
        item = self.router.dequeue_from("grill")
        assert item.name == "Burger"
        assert self.router.station_sizes()["grill"] == 0

    def test_dequeue_from_empty_raises(self):
        with pytest.raises(IndexError):
            self.router.dequeue_from("grill")

    def test_dequeue_from_unknown_station_raises(self):
        with pytest.raises(KeyError):
            self.router.dequeue_from("nonexistent")

    def test_multiple_orders_queue_up_correctly(self):
        for i in range(5):
            self.router.route_order(order_id=i, items=[make_item(1, "Burger", "mains")])
        assert self.router.station_sizes()["grill"] == 5

    def test_available_stations(self):
        assert set(self.router.available_stations()) == set(STATIONS)

    def test_even_distribution_prevents_overload(self):
        """
        10 items with unknown category should be spread roughly evenly,
        no single station has more than ceil(10/4) = 3 items.
        """
        import math
        n = 10
        items = [make_item(i, f"X{i}", "mystery") for i in range(n)]
        summary = self.router.route_order(order_id=1, items=items)
        max_allowed = math.ceil(n / len(STATIONS))
        for station in STATIONS:
            assert len(summary[station]) <= max_allowed
