from typing import Any, List, Optional


class BSTNode:
    def __init__(self, key, value: Any):
        self.key = key
        self.values: list = [value]
        self.left: Optional["BSTNode"] = None
        self.right: Optional["BSTNode"] = None
        self.height = 1


class BST:
    """AVL-balanced date tree with O(log n) worst-case search and insertion.

    Range queries are O(log n + m); inorder traversal and size accounting are
    iterative. The recursive insert/rebalance depth is logarithmically bounded
    by AVL rotations.
    """

    def __init__(self):
        self.root: Optional[BSTNode] = None
        self._size = 0

    @staticmethod
    def _height(node: Optional[BSTNode]) -> int:
        return node.height if node is not None else 0

    def _refresh_height(self, node: BSTNode) -> None:
        node.height = 1 + max(self._height(node.left), self._height(node.right))

    def _rotate_right(self, root: BSTNode) -> BSTNode:
        pivot = root.left
        root.left = pivot.right
        pivot.right = root
        self._refresh_height(root)
        self._refresh_height(pivot)
        return pivot

    def _rotate_left(self, root: BSTNode) -> BSTNode:
        pivot = root.right
        root.right = pivot.left
        pivot.left = root
        self._refresh_height(root)
        self._refresh_height(pivot)
        return pivot

    def _rebalance(self, node: BSTNode) -> BSTNode:
        self._refresh_height(node)
        balance = self._height(node.left) - self._height(node.right)
        if balance > 1:
            if self._height(node.left.left) < self._height(node.left.right):
                node.left = self._rotate_left(node.left)
            return self._rotate_right(node)
        if balance < -1:
            if self._height(node.right.right) < self._height(node.right.left):
                node.right = self._rotate_right(node.right)
            return self._rotate_left(node)
        return node

    def insert(self, key, value: Any) -> None:
        """Insert a value, appending values for duplicate keys. O(log n)."""
        self.root = self._insert(self.root, key, value)
        self._size += 1

    def _insert(self, node: Optional[BSTNode], key, value: Any) -> BSTNode:
        if node is None:
            return BSTNode(key, value)
        if key < node.key:
            node.left = self._insert(node.left, key, value)
        elif key > node.key:
            node.right = self._insert(node.right, key, value)
        else:
            node.values.append(value)
            return node
        return self._rebalance(node)

    def search(self, key) -> list:
        """Return all values at key, or [] if not found. O(log n)."""
        node = self.root
        while node is not None:
            if key == node.key:
                return list(node.values)
            node = node.left if key < node.key else node.right
        return []

    def range_query(self, low, high) -> list:
        """Return values with low <= key <= high in ascending key order."""
        result: list = []
        if low > high:
            return result
        stack: list[tuple[BSTNode, bool]] = []
        if self.root is not None:
            stack.append((self.root, False))
        while stack:
            node, emit = stack.pop()
            if emit:
                result.extend(node.values)
            elif node.key < low:
                if node.right is not None:
                    stack.append((node.right, False))
            elif node.key > high:
                if node.left is not None:
                    stack.append((node.left, False))
            else:
                if node.right is not None and node.key < high:
                    stack.append((node.right, False))
                stack.append((node, True))
                if node.left is not None and node.key > low:
                    stack.append((node.left, False))
        return result

    def inorder(self) -> List[tuple]:
        """Return (key, value) pairs in ascending key order. O(n)."""
        result: list = []
        stack: list[BSTNode] = []
        node = self.root
        while stack or node is not None:
            while node is not None:
                stack.append(node)
                node = node.left
            node = stack.pop()
            result.extend((node.key, value) for value in node.values)
            node = node.right
        return result

    def size(self) -> int:
        """Return total values stored, not nodes. O(1)."""
        return self._size

    def is_empty(self) -> bool:
        return self.root is None