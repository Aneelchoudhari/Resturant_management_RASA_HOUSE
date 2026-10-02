class TrieNode:
    def __init__(self):
        self.children: dict = {}
        self.is_end: bool = False
        self.items: list = []


class Trie:
    """Educational prefix trie with ID-aware upsert and removal operations."""

    def __init__(self):
        self.root = TrieNode()
        self._items: dict[tuple[str, object], tuple[str, object]] = {}

    def _item_key(self, item: object) -> tuple[str, object]:
        object_key = ("object", id(item))
        if object_key in self._items:
            return object_key
        item_id = getattr(item, "id", None)
        return ("id", item_id) if item_id is not None else ("object", id(item))

    def _find_node(self, word: str) -> tuple[TrieNode | None, list[tuple[TrieNode, str, TrieNode]]]:
        node = self.root
        path = []
        for character in word.lower():
            child = node.children.get(character)
            if child is None:
                return None, path
            path.append((node, character, child))
            node = child
        return node, path

    def insert(self, word: str, item: object) -> None:
        """Insert or replace one logical item in O(k) trie traversal time."""
        normalized = word.lower()
        item_key = self._item_key(item)
        existing = self._items.get(item_key)
        if existing is not None:
            old_word, old_item = existing
            self.remove(old_word, old_item)

        node = self.root
        for character in normalized:
            node = node.children.setdefault(character, TrieNode())
        node.items.append(item)
        node.is_end = True
        self._items[item_key] = (normalized, item)

    def update(self, old_word: str, new_word: str, item: object) -> None:
        """Move or replace an item after a name update."""
        self.remove(old_word, item)
        self.insert(new_word, item)

    def remove(
        self,
        word: str,
        item: object | None = None,
        *,
        item_id: object | None = None,
    ) -> bool:
        """Remove a specific item or all items at a word; prune empty nodes."""
        normalized = word.lower()
        node, path = self._find_node(normalized)
        if node is None:
            return False
        if item_id is not None:
            key = ("id", item_id)
            target_item = self._items.get(key, (None, None))[1]
            keys = [key] if target_item is not None and self._items[key][0] == normalized else []
        elif item is not None:
            key = self._item_key(item)
            keys = [key] if key in self._items and self._items[key][0] == normalized else []
        else:
            keys = [key for key, (indexed_word, _) in self._items.items() if indexed_word == normalized]
        if not keys:
            return False

        removed_items = {id(self._items[key][1]) for key in keys}
        removed_keys = set(keys)
        for key in keys:
            self._items.pop(key, None)
        node.items = [indexed_item for indexed_item in node.items if id(indexed_item) not in removed_items]
        node.is_end = bool(node.items)
        for parent, character, child in reversed(path):
            if child.children or child.items:
                break
            del parent.children[character]
        return True

    delete = remove

    def search_prefix(self, prefix: str) -> list:
        """Return matching items in O(k + subtree size), case-insensitively."""
        node, _ = self._find_node(prefix)
        if node is None:
            return []
        result = []
        stack = [node]
        while stack:
            current = stack.pop()
            result.extend(current.items)
            stack.extend(current.children.values())
        return result


class CategoryIndex:
    """Educational hash index with incremental, duplicate-safe item updates."""

    def __init__(self):
        self._index: dict[str, dict[tuple[str, object], object]] = {}
        self._items: dict[tuple[str, object], tuple[str, object]] = {}

    def _key(self, item: object) -> tuple[str, object]:
        object_key = ("object", id(item))
        if object_key in self._items:
            return object_key
        item_id = getattr(item, "id", None)
        return ("id", item_id) if item_id is not None else ("object", id(item))

    def build(self, items: list) -> None:
        """Build from a snapshot in O(n), replacing the prior snapshot."""
        self._index.clear()
        self._items.clear()
        for item in items:
            self.add(item)

    def add(self, item: object) -> None:
        """Insert or update an item; moving categories removes the old entry."""
        key = self._key(item)
        category = item.category.lower()
        old = self._items.get(key)
        if old is not None:
            old_category, _ = old
            self._index[old_category].pop(key, None)
            if not self._index[old_category]:
                del self._index[old_category]
        self._index.setdefault(category, {})[key] = item
        self._items[key] = (category, item)

    update = add

    def remove(self, item: object | None = None, *, item_id: object | None = None) -> bool:
        key = ("id", item_id) if item_id is not None else self._key(item)
        existing = self._items.pop(key, None)
        if existing is None:
            return False
        category, _ = existing
        self._index[category].pop(key, None)
        if not self._index[category]:
            del self._index[category]
        return True

    delete = remove

    def get(self, category: str) -> list:
        """Return the category's values in O(1 + m), including the result copy."""
        return list(self._index.get(category.lower(), {}).values())

    def all_categories(self) -> list:
        return sorted(self._index)