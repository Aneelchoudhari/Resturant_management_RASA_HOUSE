"""Reproducible before/after DSA benchmarks; run from any working directory.

The before functions reproduce the former request-time rebuilds and algorithms.
The after functions exercise current SQL-backed API query shapes or current DSA
implementations. Results are measurements from this run, not checked-in claims.
"""
from __future__ import annotations

import gc
import json
import statistics
import sys
import time
import tracemalloc
from bisect import bisect_left
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, create_engine, extract, func, select

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.dsa.interval_scheduler import ReservationSlot, TableSlot, allocate
from app.dsa.order_history import BST
from app.dsa.priority_queue import MinHeap, compute_priority_score
from app.dsa.table_graph import Graph
from app.dsa.trie import CategoryIndex, Trie


def median_ms(operation, repeats: int = 3) -> float | None:
    samples = []
    try:
        for _ in range(repeats):
            gc.collect()
            started = time.perf_counter()
            operation()
            samples.append((time.perf_counter() - started) * 1000)
    except RecursionError:
        return None
    return round(statistics.median(samples), 3)


def peak_kib(operation) -> float:
    gc.collect()
    tracemalloc.start()
    operation()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return round(peak / 1024, 1)


class LegacyBSTNode:
    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.left = None
        self.right = None


def legacy_bst_work(size: int) -> None:
    root = None

    def insert(node, key, value):
        if node is None:
            return LegacyBSTNode(key, value)
        if key < node.key:
            node.left = insert(node.left, key, value)
        elif key > node.key:
            node.right = insert(node.right, key, value)
        return node

    for key in range(size):
        root = insert(root, key, key)
    cursor = root
    while cursor is not None:
        cursor = cursor.right


def legacy_graph_bfs(graph: Graph, start: int) -> list[int]:
    if start not in graph._adj:
        return []
    queue = [start]
    visited = {start}
    result = []
    while queue:
        node = queue.pop(0)
        result.append(node)
        for neighbor in graph.neighbors(node):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return result


def legacy_scheduler(reservations, tables):
    sorted_reservations = sorted(reservations, key=lambda reservation: reservation.start)
    schedule = {table.table_id: [] for table in tables}
    assignments = []
    unassigned = []
    for reservation in sorted_reservations:
        eligible = sorted(
            [table for table in tables if table.capacity >= reservation.party_size],
            key=lambda table: table.capacity,
        )
        for table in eligible:
            if all(
                reservation.end <= start or reservation.start >= end
                for start, end in schedule[table.table_id]
            ):
                schedule[table.table_id].append((reservation.start, reservation.end))
                assignments.append(reservation.reservation_id)
                break
        else:
            unassigned.append(reservation.reservation_id)
    return assignments, unassigned


def menu_rows(engine, size: int):
    metadata = MetaData()
    menu = Table(
        "benchmark_menu",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("name", String, nullable=False),
        Column("category", String, nullable=False),
    )
    queue = Table(
        "benchmark_waitlist",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("priority_tier", Integer, nullable=False),
        Column("party_size", Integer, nullable=False),
        Column("joined_at", DateTime(timezone=True), nullable=False),
    )
    metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    with engine.begin() as connection:
        connection.execute(
            menu.insert(),
            [
                {"id": row_id, "name": f"Menu {row_id:06d}", "category": "mains" if row_id % 3 else "drinks"}
                for row_id in range(size)
            ],
        )
        connection.execute(
            queue.insert(),
            [
                {
                    "id": row_id,
                    "priority_tier": 1 + row_id % 3,
                    "party_size": 1 + row_id % 8,
                    "joined_at": now - timedelta(seconds=row_id * 3),
                }
                for row_id in range(size)
            ],
        )
        connection.exec_driver_sql("CREATE INDEX ix_benchmark_menu_prefix ON benchmark_menu (lower(name))")
        connection.exec_driver_sql("CREATE INDEX ix_benchmark_menu_category ON benchmark_menu (lower(category))")
    return menu, queue


def run() -> list[dict]:
    results: list[dict] = []
    sizes = (100, 1_000, 10_000, 50_000)
    for size in sizes:
        items = [
            SimpleNamespace(id=row_id, name=f"Menu {row_id:06d}", category="mains" if row_id % 3 else "drinks")
            for row_id in range(size)
        ]
        scores = [(float(size - row_id), row_id, row_id) for row_id in range(size)]
        engine = create_engine("sqlite://")
        menu, queue = menu_rows(engine, size)
        prefix = "menu 0"
        score_order = (
            queue.c.priority_tier * 1000
            + extract("epoch", queue.c.joined_at)
            - queue.c.party_size * 5
        )

        def heap_rebuild():
            heap = MinHeap()
            for score, item_id, item in scores:
                heap.push(score, item_id, item)
            heap.to_sorted_list()

        def heap_after():
            heap = MinHeap()
            heap.heapify(scores)
            heap.to_sorted_list()

        def trie_rebuild():
            trie = Trie()
            for item in items:
                trie.insert(item.name, item)
            trie.search_prefix(prefix)

        def menu_query():
            with engine.connect() as connection:
                connection.execute(
                    select(menu.c.id).where(func.lower(menu.c.name).like(prefix + "%"))
                ).all()

        def category_rebuild():
            index = CategoryIndex()
            index.build(items)
            index.get("mains")

        def category_query():
            with engine.connect() as connection:
                connection.execute(
                    select(menu.c.id).where(func.lower(menu.c.category) == "mains")
                ).all()

        def heap_sql_order():
            with engine.connect() as connection:
                connection.execute(select(queue.c.id).order_by(score_order, queue.c.id)).all()

        def heap_in_memory_order():
            heap = MinHeap()
            now = datetime.now(timezone.utc)
            for row_id in range(size):
                heap.push(compute_priority_score(1 + row_id % 3, 1 + row_id % 8, now - timedelta(seconds=row_id * 3)), row_id, row_id)
            heap.to_sorted_list()

        results.extend([
            {"operation": "heap build+sort", "n": size, "before_ms": median_ms(heap_rebuild), "after_ms": median_ms(heap_after)},
            {"operation": "menu prefix rebuild vs SQL", "n": size, "before_ms": median_ms(trie_rebuild), "after_ms": median_ms(menu_query)},
            {"operation": "category rebuild vs SQL", "n": size, "before_ms": median_ms(category_rebuild), "after_ms": median_ms(category_query)},
            {"operation": "waitlist heap sort vs SQL order", "n": size, "before_ms": median_ms(heap_in_memory_order), "after_ms": median_ms(heap_sql_order)},
        ])
        if size == 10_000:
            results.append({
                "operation": "peak temporary memory (10k items)",
                "n": size,
                "before_heap_kib": peak_kib(heap_rebuild),
                "after_heapify_kib": peak_kib(heap_after),
                "before_trie_kib": peak_kib(trie_rebuild),
                "after_menu_query_kib": peak_kib(menu_query),
                "before_category_kib": peak_kib(category_rebuild),
                "after_category_query_kib": peak_kib(category_query),
            })
        engine.dispose()

    for size in (100, 500, 900, 1_000, 10_000, 50_000):
        results.append({
            "operation": "sorted BST build+search",
            "n": size,
            "before_ms": median_ms(lambda: legacy_bst_work(size), 1),
            "after_ms": median_ms(
                lambda: _avl_work(size),
                1,
            ),
        })

    for size in (100, 1_000, 10_000, 50_000):
        graph = Graph()
        for node_id in range(1, size):
            graph.add_edge(0, node_id)
        results.append({
            "operation": "star graph BFS",
            "n": size,
            "before_ms": median_ms(lambda: legacy_graph_bfs(graph, 0)),
            "after_ms": median_ms(lambda: graph.bfs(0)),
        })

    for size in (100, 300, 600, 1_000):
        reservations = [ReservationSlot(i, i * 120.0, i * 120.0 + 60.0, 2) for i in range(size)]
        tables = [TableSlot(1, 4)]
        results.append({
            "operation": "one-table sequential scheduler",
            "n": size,
            "before_ms": median_ms(lambda: legacy_scheduler(reservations, tables), 1),
            "after_ms": median_ms(lambda: allocate(reservations, tables), 1),
        })
    return results


def _avl_work(size: int) -> None:
    tree = BST()
    for key in range(size):
        tree.insert(key, key)
    tree.search(size // 2)
    tree.range_query(size // 4, (size * 3) // 4)


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))