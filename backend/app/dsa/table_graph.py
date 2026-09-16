from typing import List, Optional


class Graph:
    """
    Undirected graph using an adjacency list (dict of sets).
    Models restaurant tables as nodes and physical adjacency as edges.

    BFS and DFS are both O(V + E).
    connected_components() is O(V + E) — runs BFS from every unvisited node.
    """

    def __init__(self):
        self._adj: dict = {}  # node_id (int) -> set of neighbor ids

    # ── node / edge management ─────────────────────────────────────────────────

    def add_node(self, node_id: int) -> None:
        """Add a node if it doesn't already exist."""
        if node_id not in self._adj:
            self._adj[node_id] = set()

    def add_edge(self, u: int, v: int) -> None:
        """Add an undirected edge between u and v. Creates nodes if needed."""
        self.add_node(u)
        self.add_node(v)
        self._adj[u].add(v)
        self._adj[v].add(u)

    def remove_edge(self, u: int, v: int) -> None:
        """Remove the edge between u and v (if it exists)."""
        if u in self._adj:
            self._adj[u].discard(v)
        if v in self._adj:
            self._adj[v].discard(u)

    def remove_node(self, node_id: int) -> None:
        """Remove a node and all its edges."""
        if node_id in self._adj:
            for neighbor in list(self._adj[node_id]):
                self._adj[neighbor].discard(node_id)
            del self._adj[node_id]

    def has_node(self, node_id: int) -> bool:
        return node_id in self._adj

    def has_edge(self, u: int, v: int) -> bool:
        return u in self._adj and v in self._adj[u]

    def neighbors(self, node_id: int) -> List[int]:
        return sorted(self._adj.get(node_id, set()))

    def nodes(self) -> List[int]:
        return sorted(self._adj.keys())

    def node_count(self) -> int:
        return len(self._adj)

    def edge_count(self) -> int:
        return sum(len(neighbors) for neighbors in self._adj.values()) // 2

    # ── BFS ────────────────────────────────────────────────────────────────────

    def bfs(self, start: int) -> List[int]:
        """
        Breadth-first traversal from start node.
        Returns nodes in BFS discovery order. O(V + E).
        """
        if start not in self._adj:
            return []

        visited: set = {start}
        queue: list = [start]   # FIFO — append to back, pop from front
        result: List[int] = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for neighbor in self.neighbors(node):   # sorted for determinism
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        return result

    # ── DFS ────────────────────────────────────────────────────────────────────

    def dfs(self, start: int) -> List[int]:
        """
        Depth-first traversal from start node (iterative, stack-based).
        Returns nodes in DFS discovery order. O(V + E).
        """
        if start not in self._adj:
            return []

        visited: set = set()
        stack: list = [start]
        result: List[int] = []

        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            result.append(node)
            # Push neighbors in reverse-sorted order so smallest is processed first
            for neighbor in reversed(self.neighbors(node)):
                if neighbor not in visited:
                    stack.append(neighbor)

        return result

    # ── connected components ───────────────────────────────────────────────────

    def connected_components(self) -> List[List[int]]:
        """
        Find all connected components using BFS from each unvisited node.
        Returns a list of components, each component is a sorted list of node ids.
        O(V + E).
        """
        visited: set = set()
        components: List[List[int]] = []

        for node in self.nodes():
            if node not in visited:
                component = self.bfs(node)
                components.append(component)
                visited.update(component)

        return components
