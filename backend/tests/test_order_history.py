import pytest
from datetime import date
from app.dsa.order_history import BST, BSTNode


# ── BSTNode tests ──────────────────────────────────────────────────────────────

class TestBSTNode:
    def test_initial_state(self):
        node = BSTNode(key=date(2024, 1, 1), value="order_1")
        assert node.key == date(2024, 1, 1)
        assert node.values == ["order_1"]
        assert node.left is None
        assert node.right is None


# ── BST insert / search tests ──────────────────────────────────────────────────

class TestBSTInsertSearch:
    def test_insert_and_search_single(self):
        bst = BST()
        bst.insert(date(2024, 1, 1), "order_a")
        assert bst.search(date(2024, 1, 1)) == ["order_a"]

    def test_search_missing_key_returns_empty(self):
        bst = BST()
        bst.insert(date(2024, 1, 1), "order_a")
        assert bst.search(date(2024, 6, 1)) == []

    def test_search_empty_bst_returns_empty(self):
        bst = BST()
        assert bst.search(date(2024, 1, 1)) == []

    def test_duplicate_key_accumulates_values(self):
        bst = BST()
        bst.insert(date(2024, 1, 1), "order_1")
        bst.insert(date(2024, 1, 1), "order_2")
        bst.insert(date(2024, 1, 1), "order_3")
        result = bst.search(date(2024, 1, 1))
        assert set(result) == {"order_1", "order_2", "order_3"}

    def test_insert_multiple_distinct_keys(self):
        bst = BST()
        bst.insert(date(2024, 1, 10), "order_10")
        bst.insert(date(2024, 1, 1), "order_1")
        bst.insert(date(2024, 1, 20), "order_20")
        assert bst.search(date(2024, 1, 1)) == ["order_1"]
        assert bst.search(date(2024, 1, 10)) == ["order_10"]
        assert bst.search(date(2024, 1, 20)) == ["order_20"]

    def test_is_empty(self):
        bst = BST()
        assert bst.is_empty()
        bst.insert(date(2024, 1, 1), "x")
        assert not bst.is_empty()

    def test_size(self):
        bst = BST()
        assert bst.size() == 0
        bst.insert(date(2024, 1, 1), "a")
        bst.insert(date(2024, 1, 2), "b")
        bst.insert(date(2024, 1, 1), "c")  # same date
        assert bst.size() == 3


# ── BST inorder tests ──────────────────────────────────────────────────────────

class TestBSTInorder:
    def test_inorder_returns_sorted_keys(self):
        bst = BST()
        bst.insert(date(2024, 3, 1), "mar")
        bst.insert(date(2024, 1, 1), "jan")
        bst.insert(date(2024, 2, 1), "feb")
        keys = [k for k, _ in bst.inorder()]
        assert keys == sorted(keys)

    def test_inorder_empty_bst(self):
        bst = BST()
        assert bst.inorder() == []

    def test_inorder_single_node(self):
        bst = BST()
        bst.insert(date(2024, 6, 15), "only")
        result = bst.inorder()
        assert len(result) == 1
        assert result[0] == (date(2024, 6, 15), "only")

    def test_inorder_with_duplicates_sorted(self):
        bst = BST()
        bst.insert(date(2024, 1, 5), "a")
        bst.insert(date(2024, 1, 3), "b")
        bst.insert(date(2024, 1, 5), "c")  # duplicate
        bst.insert(date(2024, 1, 7), "d")
        keys = [k for k, _ in bst.inorder()]
        assert keys == sorted(keys)
        assert len(keys) == 4


# ── BST range_query tests ──────────────────────────────────────────────────────

class TestBSTRangeQuery:
    def setup_method(self):
        """BST with orders spread across Jan–Jun 2024."""
        self.bst = BST()
        self.dates = [
            date(2024, 1, 5),
            date(2024, 2, 10),
            date(2024, 3, 15),
            date(2024, 4, 20),
            date(2024, 5, 25),
            date(2024, 6, 30),
        ]
        for i, d in enumerate(self.dates):
            self.bst.insert(d, f"order_{i+1}")

    def test_full_range_returns_all(self):
        result = self.bst.range_query(date(2024, 1, 1), date(2024, 12, 31))
        assert len(result) == 6

    def test_narrow_range_returns_subset(self):
        result = self.bst.range_query(date(2024, 2, 1), date(2024, 4, 30))
        assert set(result) == {"order_2", "order_3", "order_4"}

    def test_single_date_range(self):
        result = self.bst.range_query(date(2024, 3, 15), date(2024, 3, 15))
        assert result == ["order_3"]

    def test_inclusive_lower_boundary(self):
        result = self.bst.range_query(date(2024, 1, 5), date(2024, 1, 5))
        assert result == ["order_1"]

    def test_inclusive_upper_boundary(self):
        result = self.bst.range_query(date(2024, 6, 30), date(2024, 6, 30))
        assert result == ["order_6"]

    def test_empty_range_no_orders_in_window(self):
        # Gap between existing dates: Jan 6 – Feb 9 has no orders
        result = self.bst.range_query(date(2024, 1, 6), date(2024, 2, 9))
        assert result == []

    def test_range_before_all_dates(self):
        result = self.bst.range_query(date(2023, 1, 1), date(2023, 12, 31))
        assert result == []

    def test_range_after_all_dates(self):
        result = self.bst.range_query(date(2025, 1, 1), date(2025, 12, 31))
        assert result == []

    def test_range_results_in_sorted_date_order(self):
        result = self.bst.range_query(date(2024, 1, 1), date(2024, 12, 31))
        # BST range_query explores in-order, so results should come out sorted
        # We'll verify by checking the values match expected order
        assert result == [f"order_{i}" for i in range(1, 7)]

    def test_multiple_orders_same_date_all_returned(self):
        bst = BST()
        bst.insert(date(2024, 5, 1), "morning_order")
        bst.insert(date(2024, 5, 1), "evening_order")
        result = bst.range_query(date(2024, 5, 1), date(2024, 5, 1))
        assert set(result) == {"morning_order", "evening_order"}

    def test_empty_bst_range_query(self):
        bst = BST()
        assert bst.range_query(date(2024, 1, 1), date(2024, 12, 31)) == []

    def test_inverted_range_returns_empty(self):
        # from > to — no valid keys can satisfy this
        result = self.bst.range_query(date(2024, 6, 1), date(2024, 1, 1))
        assert result == []
