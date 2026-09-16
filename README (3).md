# Restaurant Management System — Implementation Plan

A full-stack Restaurant Management System built to demonstrate applied Data Structures & Algorithms (DSA) inside a real, working product — not as isolated exercises.

This document is the step-by-step build plan, from project init to deployment.

---

## Tech Stack

- **Backend:** Python, FastAPI
- **Database:** PostgreSQL + SQLAlchemy + Alembic (migrations)
- **Frontend:** React (Vite)
- **Auth:** JWT (staff / admin roles)
- **Testing:** Pytest
- *(Docker, CI, and deployment are intentionally deferred — see note at the end of this document)*

---

## DSA Modules Overview

| # | Module | Data Structure / Algorithm | Complexity Highlight |
|---|--------|------------------------------|------------------------|
| 1 | Waitlist | Priority Queue (min-heap, self-implemented) | O(log n) insert/pop vs O(n) naive sorted list |
| 2 | Table Allocation | Interval Scheduling (greedy) | O(n log n) |
| 3 | Menu Search | Trie + Hash Map | O(k) prefix search vs O(n·k) naive scan |
| 4 | Kitchen Order Routing | Multiple Queues (round-robin / weighted) | O(1) enqueue/dequeue per station |
| 5 | Order History | Binary Search Tree / sorted index | O(log n) lookup, O(log n + m) range query |
| 6 *(stretch)* | Table Adjacency | Graph (BFS/DFS) | O(V + E) traversal for combining tables |

Each module is implemented from scratch in `backend/app/dsa/` — no shortcuts via built-in libraries like `heapq` for the core logic, so the implementation itself is demonstrable in interviews.

---

## Phase 0 — Project Scaffolding

- [ ] Create root repo with `backend/`, `frontend/`, and top-level `docker-compose.yml`
- [ ] Initialize git, add `.gitignore` (Python, Node, env files)
- [ ] Write `.env.example` for DB credentials and secrets
- [ ] Set up `docker-compose.yml` with three services: `postgres`, `backend`, `frontend`
- [ ] Confirm `docker-compose up` brings up an empty skeleton of all three containers talking to each other

---

## Phase 1 — Backend Foundation

- [ ] Set up FastAPI app skeleton (`app/main.py`)
- [ ] Configure SQLAlchemy connection to PostgreSQL
- [ ] Define core models: `tables`, `reservations`, `waitlist_entries`, `menu_items`, `orders`, `staff`
- [ ] Set up Alembic, create first migration
- [ ] Add Pydantic schemas for request/response validation
- [ ] Build basic CRUD routes for tables, menu items, staff (no DSA yet — just plumbing)
- [ ] Confirm Swagger docs work at `/docs`

---

## Phase 2 — Waitlist Module (Priority Queue)

- [ ] Implement a min-heap from scratch in `dsa/priority_queue.py`
- [ ] Priority score = function of wait time + party size + priority tier
- [ ] Route: `POST /waitlist/join` — adds entry, returns queue position
- [ ] Route: `GET /waitlist` — returns current queue order
- [ ] Write Pytest unit tests for the heap (insert, pop, ordering correctness, edge cases)

---

## Phase 3 — Table Allocation Module (Interval Scheduling)

- [ ] Implement greedy interval-scheduling allocator in `dsa/interval_scheduler.py`
- [ ] Input: list of reservations (start time, duration, party size) + available tables
- [ ] Output: table assignments minimizing idle time / conflicts
- [ ] Route: `GET /tables/allocate`
- [ ] Write Pytest tests: overlapping intervals, edge cases (exact time boundaries, no capacity match)

---

## Phase 4 — Menu Search Module (Trie + Hash Map)

- [ ] Implement Trie from scratch in `dsa/trie.py` for prefix search
- [ ] Implement hash map indexing for category/tag lookups
- [ ] Route: `GET /menu/search?q=` — prefix autocomplete
- [ ] Route: `GET /menu/category/{tag}` — O(1) category lookup
- [ ] Write Pytest tests: prefix matching, case sensitivity, empty query, no matches

---

## Phase 5 — Kitchen Order Routing (Multiple Queues)

- [ ] Implement per-station queues (grill, dessert, drinks, etc.) in `dsa/order_router.py`
- [ ] Round-robin or weighted distribution logic to prevent one station from backing up
- [ ] Route: `POST /orders` — order gets split and routed to relevant station queues
- [ ] Route: `GET /kitchen/{station}` — view a station's current queue
- [ ] Write Pytest tests: even distribution, station overload handling

---

## Phase 6 — Order History Module (BST / Sorted Index)

- [ ] Implement a BST (or sorted structure) in `dsa/order_history.py` keyed by date
- [ ] Support point lookup (single date/customer) and range queries (date range)
- [ ] Route: `GET /orders/history?from=&to=`
- [ ] Write Pytest tests: insertion, range query correctness, empty range

---

## Phase 7 *(Stretch)* — Table Adjacency Graph

- [ ] Model tables as graph nodes, adjacency as edges
- [ ] Implement BFS/DFS in `dsa/table_graph.py` to find connected table groups for large parties
- [ ] Route: `GET /tables/combine?party_size=`
- [ ] Write Pytest tests: connected components, disconnected tables

---

## Phase 8 — Authentication

- [ ] Implement JWT-based auth (staff / admin roles)
- [ ] Protect write routes (order creation, table allocation trigger) behind staff auth
- [ ] Basic login/register routes

---

## Phase 9 — Frontend (React)

- [ ] Scaffold React app with Vite
- [ ] **Waitlist Dashboard** — live queue view, add/remove entries, visual priority indicator
- [ ] **Table Map** — grid view of tables, color-coded status, refreshes after allocation runs
- [ ] **Menu Search Bar** — live autocomplete as you type
- [ ] **Reservation Form** — feeds into waitlist + allocator
- [ ] **Kitchen View** — per-station order queues
- [ ] **Order History Page** — date range filter
- [ ] **Login Page** — staff/admin auth
- [ ] Wire all pages to backend API (Axios/fetch)

---

## Phase 10 — Testing (local only)

- [ ] Confirm full Pytest suite passes locally
- [ ] Manually verify the app runs end-to-end (backend + frontend) on your own machine

---

## Phase 11 — Documentation & Resume Polish

- [ ] Write architecture diagram (React ↔ FastAPI ↔ PostgreSQL, Docker boxes)
- [ ] Write **"Algorithms & Complexity"** section explaining each DSA choice and its Big-O, in plain language
- [ ] Add screenshots / short GIF demo of key features (waitlist, live search, table map)
- [ ] Add "How to run locally" (plain `uvicorn` + `npm run dev` instructions) and "How to run tests"
- [ ] Final resume bullet drafts, e.g.:
  - "Designed and implemented a full-stack restaurant management system using FastAPI, PostgreSQL, and React, featuring five self-implemented data structures (priority queue, greedy interval scheduler, Trie, multi-queue router, BST) powering core business logic."

---

## Suggested Order Summary

0 → Scaffolding → 1 → Backend Foundation → 2–7 → DSA Modules (in order) → 8 → Auth → 9 → Frontend → 10 → Local Testing → 11 → Docs/Polish

Each phase is meant to be completable and demoable on its own — so if time runs short before placements, the project is still resume-ready at the end of any completed phase from Phase 4 onward.

---


