# Algorithms and Complexity

This project uses several self-implemented data structures and algorithms to drive restaurant operations. Each structure is intentionally built from scratch to show real-world tradeoffs and interview-ready reasoning.

## 1) Priority Queue: Min-Heap

Purpose: manage the waitlist so the most urgent guest is served first.

The implementation in `backend/app/dsa/priority_queue.py` stores entries as tuples of `(score, item_id, item)`. The heap property keeps the lowest score at the root, which ensures fast prioritization.

- Insert: `O(log n)`
- Peek: `O(1)`
- Pop lowest priority: `O(log n)`
- Sorting the entire queue: `O(n log n)`

Why not just sort a list each time? A naive approach would repeatedly scan or sort the whole collection, which becomes expensive as the queue grows. The heap keeps the queue ordered incrementally while avoiding full recomputation.

## 2) Greedy Interval Scheduling

Purpose: assign reservations to tables without overlaps.

The scheduler sorts reservations by end time and greedily selects the earliest finishing reservation that fits within the table capacity and time constraints. This is an efficient approach when you want to maximize occupied time while avoiding conflicts.

- Sort: `O(n log n)`
- Allocation pass: `O(n)`
- Total: `O(n log n)`

A brute-force version would test every reservation against every table and every other reservation, leading to roughly `O(n^2)` or worse in practical use.

## 3) Trie for Prefix Search

Purpose: provide fast menu autocomplete.

The trie stores characters as nodes, so searching for a prefix is proportional to the length of the query rather than the number of menu items.

- Prefix search: `O(k)` where `k` is the query length
- Build time: `O(total characters)`

A naive linear scan would compare the query to every menu item and can become `O(n * k)` in the worst case.

## 4) Queue for Kitchen Routing

Purpose: distribute orders to kitchen stations such as grill, drinks, desserts, and sides.

The queue is implemented as a singly linked list to support constant-time enqueue and dequeue operations. This makes station queue management efficient and simple.

- Enqueue: `O(1)`
- Dequeue: `O(1)`
- Viewed queue length: `O(1)` or `O(n)` depending on implementation detail

This is more efficient than trying to remove from the middle of a list or re-sorting the entire station queue after each order.

## 5) Binary Search Tree for Order History

Purpose: support date-based lookups and ranges for order history.

The BST stores dates as keys and orders as values. This supports quick lookups and ordered traversal for ranges.

- Insert: `O(log n)` on average
- Search by date: `O(log n)` on average
- Range query: `O(log n + m)` where `m` is the number of results returned

A full scan of all orders would be `O(n)`, which gets worse as history grows.

## 6) Graph for Table Adjacency and Grouping

Purpose: model connected tables for large parties and adjacency checks.

The graph stores a table adjacency list and uses iterative BFS/DFS to find connected groups.

- BFS/DFS traversal: `O(V + E)`
- Connected components: `O(V + E)`

This is the standard complexity for graph traversal and allows the app to discover groups of adjacent tables efficiently.

## Summary

The core theme of the project is selecting the right structure for the right task:

- Heap for priority order
- Greedy scheduling for resource assignment
- Trie for prefix lookup
- Queue for ordered processing
- BST for sorted historical queries
- Graph for connectivity and grouping

This makes the system not just a demo app, but a practical case study in applied data structures.
