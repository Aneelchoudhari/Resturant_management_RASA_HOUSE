from typing import Any, List, Optional


class BSTNode:
    def __init__(self, key, value: Any):
        self.key = key
        self.values: list = [value]  # multiple orders can share the same date
        self.left: Optional["BSTNode"] = None
        self.right: Optional["BSTNode"] = None


class BST:
    """
    Binary Search Tree keyed by date, implemented from scratch.

    Supports:
      insert   — O(log n) average, O(n) worst (unbalanced)
      search   — O(log n) average
      range_query — O(log n + m) where m = number of matching items
      inorder  — O(n), returns all items in sorted key order
    """

    def __init__(self):
        self.root: Optional[BSTNode] = None

    # ── insert ─────────────────────────────────────────────────────────────────

    def insert(self, key, value: Any) -> None:
        """Insert value at key. Duplicate keys append to the existing node's list."""
        self.root = self._insert(self.root, key, value)

    def _insert(self, node: Optional[BSTNode], key, value: Any) -> BSTNode:
        if node is None:
            return BSTNode(key, value)
        if key < node.key:
            node.left = self._insert(node.left, key, value)
        elif key > node.key:
            node.right = self._insert(node.right, key, value)
        else:
            node.values.append(value)  # same key → accumulate
        return node

    # ── search ─────────────────────────────────────────────────────────────────

    def search(self, key) -> list:
        """Return all values at key, or [] if not found. O(log n) average."""
        node = self._search(self.root, key)
        return list(node.values) if node else []

    def _search(self, node: Optional[BSTNode], key) -> Optional[BSTNode]:
        if node is None or node.key == key:
            return node
        if key < node.key:
            return self._search(node.left, key)
        return self._search(node.right, key)

    # ── range query ────────────────────────────────────────────────────────────

    def range_query(self, low, high) -> list:
        """
        Return all values whose key satisfies low <= key <= high.
        O(log n + m) — prunes subtrees outside the range.
        """
        result: list = []
        self._range_query(self.root, low, high, result)
        return result

    def _range_query(self, node: Optional[BSTNode], low, high, result: list) -> None:
        if node is None:
            return
        # Only explore left subtree if it could contain keys >= low
        if node.key > low:
            self._range_query(node.left, low, high, result)
        # Include this node if its key is within range
        if low <= node.key <= high:
            result.extend(node.values)
        # Only explore right subtree if it could contain keys <= high
        if node.key < high:
            self._range_query(node.right, low, high, result)

    # ── inorder ────────────────────────────────────────────────────────────────

    def inorder(self) -> List[tuple]:
        """Return (key, value) pairs for all entries in ascending key order. O(n)."""
        result: list = []
        self._inorder(self.root, result)
        return result

    def _inorder(self, node: Optional[BSTNode], result: list) -> None:
        if node is None:
            return
        self._inorder(node.left, result)
        for v in node.values:
            result.append((node.key, v))
        self._inorder(node.right, result)

    # ── helpers ────────────────────────────────────────────────────────────────

    def size(self) -> int:
        """Return total number of values stored (not nodes). O(n)."""
        return sum(1 for _ in self.inorder())

    def is_empty(self) -> bool:
        return self.root is None
