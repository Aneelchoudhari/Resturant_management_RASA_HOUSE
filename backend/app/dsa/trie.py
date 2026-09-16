class TrieNode:
    def __init__(self):
        self.children: dict = {}
        self.is_end: bool = False
        self.items: list = []  # menu items stored at terminal nodes


class Trie:
    """
    Trie (prefix tree) built from scratch for O(k) prefix search,
    where k is the length of the query string.

    Each character of a menu item name occupies one node.
    Items are stored at the terminal node of their name so that
    _collect() can gather all matches under a prefix in one DFS pass.
    """

    def __init__(self):
        self.root = TrieNode()

    def insert(self, word: str, item: object) -> None:
        """
        Insert word (stored lowercased) and attach item at its terminal node.
        O(k) where k = len(word).
        """
        node = self.root
        for ch in word.lower():
            if ch not in node.children:
                node.children[ch] = TrieNode()
            node = node.children[ch]
        node.is_end = True
        node.items.append(item)

    def search_prefix(self, prefix: str) -> list:
        """
        Return all items whose name starts with prefix (case-insensitive).
        O(k + m) where k = len(prefix), m = number of matching items.
        Empty prefix returns all inserted items.
        """
        node = self.root
        for ch in prefix.lower():
            if ch not in node.children:
                return []
            node = node.children[ch]
        return self._collect(node)

    def _collect(self, node: TrieNode) -> list:
        """DFS from node to gather all items in the subtree."""
        result = []
        if node.is_end:
            result.extend(node.items)
        for child in node.children.values():
            result.extend(self._collect(child))
        return result


class CategoryIndex:
    """
    Hash map (dict) index: category -> [items].
    Build once from the full item list; lookup is O(1).
    """

    def __init__(self):
        self._index: dict = {}

    def build(self, items: list) -> None:
        """Index items by their category (case-insensitive key). O(n)."""
        self._index = {}
        for item in items:
            key = item.category.lower()
            if key not in self._index:
                self._index[key] = []
            self._index[key].append(item)

    def get(self, category: str) -> list:
        """Return all items in a category. O(1)."""
        return self._index.get(category.lower(), [])

    def all_categories(self) -> list:
        """Return sorted list of all indexed category names."""
        return sorted(self._index.keys())
