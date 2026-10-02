import pytest
from app.dsa.table_graph import Graph


# ── helpers ────────────────────────────────────────────────────────────────────

def make_graph(edges=None, nodes=None):
    g = Graph()
    for n in (nodes or []):
        g.add_node(n)
    for u, v in (edges or []):
        g.add_edge(u, v)
    return g


# ── node / edge management ─────────────────────────────────────────────────────

class TestGraphStructure:
    def test_add_node(self):
        g = Graph()
        g.add_node(1)
        assert g.has_node(1)
        assert g.node_count() == 1

    def test_add_duplicate_node_is_idempotent(self):
        g = Graph()
        g.add_node(1)
        g.add_node(1)
        assert g.node_count() == 1

    def test_add_edge_creates_both_nodes(self):
        g = Graph()
        g.add_edge(1, 2)
        assert g.has_node(1)
        assert g.has_node(2)

    def test_add_edge_undirected(self):
        g = Graph()
        g.add_edge(1, 2)
        assert g.has_edge(1, 2)
        assert g.has_edge(2, 1)

    def test_has_edge_false_before_adding(self):
        g = Graph()
        g.add_node(1)
        g.add_node(2)
        assert not g.has_edge(1, 2)

    def test_remove_edge(self):
        g = make_graph(edges=[(1, 2), (2, 3)])
        g.remove_edge(1, 2)
        assert not g.has_edge(1, 2)
        assert not g.has_edge(2, 1)
        assert g.has_edge(2, 3)  # other edge unaffected

    def test_remove_nonexistent_edge_no_error(self):
        g = Graph()
        g.add_node(1)
        g.remove_edge(1, 99)  # should not raise

    def test_remove_node(self):
        g = make_graph(edges=[(1, 2), (1, 3)])
        g.remove_node(1)
        assert not g.has_node(1)
        assert not g.has_edge(2, 1)
        assert not g.has_edge(3, 1)

    def test_neighbors_sorted(self):
        g = make_graph(edges=[(1, 4), (1, 2), (1, 3)])
        assert g.neighbors(1) == [2, 3, 4]

    def test_edge_count(self):
        g = make_graph(edges=[(1, 2), (2, 3), (3, 4)])
        assert g.edge_count() == 3

    def test_empty_graph(self):
        g = Graph()
        assert g.node_count() == 0
        assert g.edge_count() == 0
        assert g.nodes() == []


# ── BFS tests ──────────────────────────────────────────────────────────────────

class TestBFS:
    def test_bfs_single_node(self):
        g = make_graph(nodes=[1])
        assert g.bfs(1) == [1]

    def test_bfs_linear_chain(self):
        g = make_graph(edges=[(1, 2), (2, 3), (3, 4)])
        assert g.bfs(1) == [1, 2, 3, 4]

    def test_bfs_star_graph(self):
        # Centre=1 connected to 2, 3, 4
        g = make_graph(edges=[(1, 2), (1, 3), (1, 4)])
        result = g.bfs(1)
        assert result[0] == 1
        assert set(result[1:]) == {2, 3, 4}

    def test_bfs_visits_all_in_connected_graph(self):
        g = make_graph(edges=[(1, 2), (1, 3), (2, 4), (3, 4)])
        assert set(g.bfs(1)) == {1, 2, 3, 4}

    def test_bfs_unknown_start_returns_empty(self):
        g = make_graph(nodes=[1])
        assert g.bfs(99) == []

    def test_bfs_does_not_revisit_nodes(self):
        g = make_graph(edges=[(1, 2), (2, 3), (3, 1)])  # cycle
        result = g.bfs(1)
        assert len(result) == len(set(result))  # no duplicates

    def test_bfs_empty_graph(self):
        g = Graph()
        assert g.bfs(1) == []

    def test_bfs_large_star_graph(self):
        graph = make_graph(edges=[(0, node_id) for node_id in range(1, 10001)])
        result = graph.bfs(0)
        assert len(result) == 10001
        assert result[:4] == [0, 1, 2, 3]


# ── DFS tests ──────────────────────────────────────────────────────────────────

class TestDFS:
    def test_dfs_single_node(self):
        g = make_graph(nodes=[1])
        assert g.dfs(1) == [1]

    def test_dfs_linear_chain(self):
        g = make_graph(edges=[(1, 2), (2, 3), (3, 4)])
        assert g.dfs(1) == [1, 2, 3, 4]

    def test_dfs_visits_all_in_connected_graph(self):
        g = make_graph(edges=[(1, 2), (1, 3), (2, 4), (3, 4)])
        assert set(g.dfs(1)) == {1, 2, 3, 4}

    def test_dfs_unknown_start_returns_empty(self):
        g = make_graph(nodes=[1])
        assert g.dfs(99) == []

    def test_dfs_does_not_revisit_nodes(self):
        g = make_graph(edges=[(1, 2), (2, 3), (3, 1)])  # cycle
        result = g.dfs(1)
        assert len(result) == len(set(result))

    def test_dfs_empty_graph(self):
        g = Graph()
        assert g.dfs(1) == []


# ── connected_components tests ─────────────────────────────────────────────────

class TestConnectedComponents:
    def test_fully_connected_graph_one_component(self):
        g = make_graph(edges=[(1, 2), (2, 3), (3, 4)])
        components = g.connected_components()
        assert len(components) == 1
        assert set(components[0]) == {1, 2, 3, 4}

    def test_two_disconnected_groups(self):
        # Group A: 1-2-3, Group B: 4-5
        g = make_graph(edges=[(1, 2), (2, 3), (4, 5)])
        components = g.connected_components()
        assert len(components) == 2
        sets = [set(c) for c in components]
        assert {1, 2, 3} in sets
        assert {4, 5} in sets

    def test_all_isolated_nodes(self):
        g = make_graph(nodes=[1, 2, 3, 4])
        components = g.connected_components()
        assert len(components) == 4
        assert all(len(c) == 1 for c in components)

    def test_single_node_graph(self):
        g = make_graph(nodes=[1])
        components = g.connected_components()
        assert components == [[1]]

    def test_empty_graph_no_components(self):
        g = Graph()
        assert g.connected_components() == []

    def test_three_separate_groups(self):
        g = make_graph(edges=[(1, 2), (3, 4), (5, 6)])
        components = g.connected_components()
        assert len(components) == 3

    def test_adding_edge_merges_components(self):
        g = make_graph(nodes=[1, 2, 3, 4])  # 4 isolated nodes
        assert len(g.connected_components()) == 4
        g.add_edge(1, 2)
        assert len(g.connected_components()) == 3
        g.add_edge(3, 4)
        assert len(g.connected_components()) == 2
        g.add_edge(2, 3)
        assert len(g.connected_components()) == 1

    def test_removing_edge_splits_component(self):
        g = make_graph(edges=[(1, 2), (2, 3)])  # linear: 1-2-3
        assert len(g.connected_components()) == 1
        g.remove_edge(1, 2)
        components = g.connected_components()
        assert len(components) == 2

    def test_no_node_appears_in_two_components(self):
        g = make_graph(edges=[(1, 2), (3, 4), (5, 6), (7, 8)])
        components = g.connected_components()
        all_nodes = [n for c in components for n in c]
        assert len(all_nodes) == len(set(all_nodes))  # no duplicates across components
