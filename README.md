# RASA HOUSE: Restaurant Management System

A complete web application that runs the day-to-day operations of a restaurant: guests reserve tables and order food, the host manages the queue and seating, the kitchen works through tickets, the cashier closes bills, and the owner watches the whole business from one dashboard.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-5-646CFF?logo=vite&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)

---

## Table of contents

1. [What is this project? (plain English)](#1-what-is-this-project-plain-english)
2. [A day in the restaurant](#2-a-day-in-the-restaurant)
3. [Who uses the system](#3-who-uses-the-system)
4. [Feature overview](#4-feature-overview)
5. [Technology stack](#5-technology-stack)
6. [Architecture](#6-architecture)
7. [Project structure](#7-project-structure)
8. [Getting started](#8-getting-started)
9. [Configuration](#9-configuration)
10. [How the main workflows work](#10-how-the-main-workflows-work)
11. [Data structures and algorithms](#11-data-structures-and-algorithms)
12. [Database design](#12-database-design)
13. [Security](#13-security)
14. [API reference](#14-api-reference)
15. [Frontend pages](#15-frontend-pages)
16. [Testing and benchmarks](#16-testing-and-benchmarks)
17. [Known limitations and future work](#17-known-limitations-and-future-work)
18. [Glossary](#18-glossary)
19. [Author](#19-author)

---

## 1. What is this project? (plain English)

Running a restaurant involves a lot of small coordination problems happening at the same time:

- A family of six walks in, but every table is full. Who gets seated next?
- Someone books a table for 8 PM. How do we make sure nobody else is given that table at 8:15?
- A waiter takes an order for a steak, a mojito and a brownie. These need to reach three different cooks, each working at their own station.
- The bill is paid, and a regular customer wants to use their reward points.
- At the end of the day, the owner wants to know how much was earned and who did what.

On paper or on a whiteboard, these things get messy. This project replaces the whiteboard with software.

**RASA HOUSE** is a fictional restaurant (Indian and western kitchen) used as the setting. The software behind it is a real, working system with two sides:

- **A website for guests**, where anyone can browse the menu, join the waiting line, book a table, create an account, place an order and collect loyalty points.
- **A staff portal**, where each employee sees only the screens and buttons that belong to their job: host, waiter, chef, cashier, manager or admin.

Behind the screens there is a server that enforces the rules (for example, *two bookings cannot overlap on the same table*) and a database that remembers everything.

---

## 2. A day in the restaurant

Here is how one evening looks through the system. You do not need any technical knowledge to follow it.

**5:30 PM, a guest books ahead.**
Meera opens the website, creates a free account and reserves a table for four at 8:00 PM for 90 minutes. The system checks that the time is in the future and that the booking is valid. Because she is signed in, she earns 10 loyalty points. A second click on the "Reserve" button by accident does not create a duplicate booking, because every request carries a unique "ticket number" that the server recognises.

**6:00 PM, the host plans the evening.**
The host opens the Floor Plan and clicks **Run Allocator**. The system looks at all the unassigned bookings and proposes which table should take which booking, always choosing the *smallest table that still fits the party* so that big tables stay free for big groups. The host reviews the proposal and saves it. Nothing is final until the host confirms.

**7:15 PM, a walk-in arrives.**
Rohan and two friends show up without a booking. The host adds them to the waiting line. The line is not simply first-come-first-served: VIP guests and people with reservations are ranked ahead of walk-ins, but anyone who has waited a long time slowly climbs the line, so nobody is ignored forever.

**7:40 PM, a table frees up.**
The host presses **Seat** next to Rohan's group and picks a table. The system checks that the table is free, big enough, and not promised to someone with a booking soon. The table turns to "occupied".

**7:50 PM, a large party.**
Twelve people arrive and no single table seats them. The host asks the system which **neighbouring tables can be pushed together**. The system knows which tables physically touch each other and suggests groups that add up to enough seats.

**8:00 PM, ordering.**
The waiter enters the order for Table 5: two tandoori chickens, one pasta, two drinks, one dessert. The system:
1. checks every item is available and in stock,
2. calculates the total, and reduces the stock,
3. splits the order into **kitchen tickets**, one per portion, and sends each to the right station (grill, drinks, desserts, sides).

**8:10 PM, the kitchen.**
At the grill station, a cook sees a live list of tickets. They **claim** one (so no other cook takes the same dish), **start** it, and mark it **complete**. When every ticket of an order is done, the order automatically becomes **Ready** and the waiter is notified on their screen.

**9:20 PM, the bill.**
The cashier opens the order, picks UPI, card or cash, and closes it. If the customer has collected 100 or more loyalty points, a discount is applied automatically and the points are used up.

**11:00 PM, the owner reviews.**
The admin dashboard shows today's bookings, revenue, table and order status, low-stock items and a log of recent staff activity. A 7-day report shows how the week is going.

---

## 3. Who uses the system

| Person | What they can do |
|---|---|
| **Guest** (not signed in) | Browse the menu, search dishes, join the walk-in waiting line, see how long the line is, make a reservation. |
| **Customer** (signed in) | Everything a guest can do, plus: place orders from a cart, see their own orders and reservations, earn and view loyalty points. |
| **Host / Receptionist** | Manage the waiting line (including VIP and reservation entries), seat guests, run the table allocator, combine tables for large parties, confirm or cancel reservations, update table status. |
| **Waiter** | Create orders for tables, follow active orders, mark orders served, process bills, cancel orders, see the floor map, seat guests from the line. |
| **Chef / Kitchen staff** | See station queues, claim, start, complete or release tickets, mark orders accepted, preparing or ready, switch a dish on or off the menu when it runs out. |
| **Cashier** | See bills awaiting payment and close them with UPI, card or cash. |
| **Manager** | Almost everything a floor team can do, plus menu editing (except prices), table settings, table adjacency and kitchen oversight. |
| **Admin** | Everything. Creates employee accounts, sets prices, adds or removes tables and menu items, allocates tables directly, reads reports and the audit log. |

Staff accounts can **only** be created by an admin. There is no public staff sign-up.

---

## 4. Feature overview

### For guests and customers

- Landing page and customer home with restaurant information
- Menu with **live search-as-you-type** and category filters
- Cart and **online ordering** (dine-in, tied to a table) for signed-in customers
- **Table reservation** with party size, date, time and duration
- **Walk-in waiting line** with a public "people in the queue" counter
- Customer accounts with **loyalty points** and a personal dashboard (orders and reservations)

### For the restaurant floor

- **Waitlist** with a fair priority system (VIP, reservation, walk-in)
- **Seating** that verifies table availability, capacity and conflicting bookings
- **Automatic table allocation** proposals for upcoming reservations
- **Table combining** for large groups using table adjacency
- Floor map with live table status: available, occupied, reserved, cleaning

### For the kitchen

- **Four stations**: grill, dessert, drinks, sides
- One ticket per portion, routed automatically by menu category
- Claim, start, complete and release workflow so two cooks never work the same ticket
- Order status moves automatically as tickets are finished
- Stock is reduced when an order is placed; dishes can be switched off when they run out

### For payments and loyalty

- Pay with UPI, card or cash (the payment method is recorded)
- Loyalty points earned for reservations and VIP or reservation queue entries
- Redemption at the till: each 100 points gives ₹100 off, capped at the bill amount

### For management

- Admin dashboard: bookings today, revenue today, table and order status, menu availability, low-stock count, active staff
- 7-day report of bookings, orders and revenue
- Employee account management (create, edit, deactivate, delete)
- **Audit log** of important admin actions
- Direct "master" table allocation by the admin

### Engineering features

- Role-based access control on every protected endpoint
- JWT login with bcrypt password hashing and login and registration rate limits
- **Idempotency keys** so a double click never creates a double booking or double order
- Row-level database locks to stop two people grabbing the same table at once
- Database check constraints, unique constraints and composite indexes
- Versioned database migrations (Alembic, 9 migrations)
- Hand-written data structures and algorithms (see section 11)
- 200+ automated tests and a reproducible benchmark script
- Full Docker Compose setup (PostgreSQL, backend, frontend)

---

## 5. Technology stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | React 18, React Router 6, Vite 5 | Single-page web app with role-based screens |
| Backend | Python 3.11, FastAPI 0.111, Uvicorn | REST API and business rules |
| Data access | SQLAlchemy 2.0, Alembic 1.13 | ORM and database migrations |
| Database | PostgreSQL 15 | Permanent storage (hosted PostgreSQL such as Supabase is also supported through configuration) |
| Validation | Pydantic 2 | Request and response validation |
| Security | python-jose (JWT), passlib + bcrypt | Tokens and password hashing |
| Testing | pytest, httpx | Unit and API tests (in-memory SQLite) |
| DevOps | Docker, Docker Compose | One-command local environment |

---

## 6. Architecture

```mermaid
flowchart LR
    Browser["React app (Vite)<br/>guest, customer and staff screens"] -->|"HTTP /api/*"| API["FastAPI backend<br/>routers, auth, business rules"]
    API --> DSA["DSA modules<br/>scheduler, graph, queues, heap, trie, AVL tree"]
    API --> DB[("PostgreSQL")]
    Alembic["Alembic migrations"] --> DB
```

How a request travels:

1. The browser calls `/api/...`. In development, Vite forwards these calls to the backend and removes the `/api` prefix.
2. FastAPI reads the login token, finds out who the user is and what role they have, and checks whether that role is allowed to perform the action.
3. The router applies the business rules, using the algorithms in `app/dsa` where relevant.
4. SQLAlchemy reads or writes PostgreSQL, using locks and constraints to keep data consistent.
5. The result is sent back as JSON and the React page updates.

**Design principle:** PostgreSQL is the single source of truth. The server does not keep important state (such as queues) only in memory, so a restart never loses a booking, a waiting guest or a kitchen ticket.

---

## 7. Project structure

```text
Resturant_management_RASA_HOUSE/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, CORS, router registration
│   │   ├── models.py               # Database tables (SQLAlchemy)
│   │   ├── schemas.py              # Request/response validation (Pydantic)
│   │   ├── auth.py                 # JWT, password hashing, role guards
│   │   ├── database.py             # Engine and session setup
│   │   ├── security_settings.py    # Production safety checks for secrets
│   │   ├── rate_limit.py           # Login/registration rate limiter
│   │   ├── reservation_rules.py    # Overlap check for table bookings
│   │   ├── kitchen_queue.py        # Creates and reads kitchen tickets
│   │   ├── dsa/                    # Hand-written data structures and algorithms
│   │   │   ├── priority_queue.py   #   Min-heap + waitlist priority score
│   │   │   ├── interval_scheduler.py#  Greedy table allocation
│   │   │   ├── trie.py             #   Prefix search + category index
│   │   │   ├── order_router.py     #   Linked-list queue + station routing
│   │   │   ├── order_history.py    #   Balanced (AVL) date tree
│   │   │   └── table_graph.py      #   Graph, BFS, DFS, connected components
│   │   └── routers/                # API endpoints, one file per area
│   │       ├── auth_router.py  tables.py  menu.py  staff.py
│   │       ├── waitlist.py  reservations.py  allocation.py  graph.py
│   │       └── orders.py  admin.py
│   ├── alembic/versions/           # 9 database migrations (0001 to 0009)
│   ├── scripts/bootstrap_admin.py  # Creates the first admin account
│   ├── benchmarks/benchmark_dsa.py # Reproducible performance measurements
│   ├── tests/                      # Automated tests
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pytest.ini
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 # Routes and role-based route guards
│   │   ├── api.js                  # All backend calls in one place
│   │   ├── auth.js                 # Reads the role from the login token
│   │   ├── components/NavBar.jsx
│   │   └── pages/                  # One file per screen
│   ├── vite.config.js              # Dev server and /api proxy
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml              # PostgreSQL + backend + frontend
├── e2e_tests.py                    # Optional end-to-end script
├── .env.example                    # Template for configuration
└── README.md
```

---

## 8. Getting started

### Prerequisites

- **Docker and Docker Compose** (recommended), or
- **Python 3.11+**, **Node.js 18+** (the Docker image uses Node 20) and a **PostgreSQL 15** database

### Option A: Docker (recommended)

**1. Get the code**

```bash
git clone https://github.com/Aneelchoudhari/Resturant_management_RASA_HOUSE.git
cd Resturant_management_RASA_HOUSE
```

**2. Create your configuration file**

```bash
cp .env.example .env
```

The defaults work for local development. Change the passwords and the `SECRET_KEY` before using anything real.

**3. Start everything**

```bash
docker compose up --build
```

This starts three containers: the PostgreSQL database, the backend (which applies all database migrations automatically before it starts) and the frontend.

**4. Create the first admin account**

Open a second terminal in the project folder:

```bash
docker compose exec backend python scripts/bootstrap_admin.py \
  --email admin@example.com --password "ChooseAStrongPassword" --name "Admin"
```

**5. Open the app**

| What | Address |
|---|---|
| Website and staff portal | http://localhost:5173 |
| Interactive API documentation | http://localhost:8000/docs |
| Database (local access only) | localhost:5432 |

**6. First steps inside the app**

1. Open http://localhost:5173/staff/select, choose the admin workspace and sign in.
2. On the admin dashboard, **add tables** (number and seat count).
3. Add **menu items** (name, category, price, stock). The project does not ship with sample menu data, so the guest menu stays empty until you add some.
4. Open **Employee Accounts** and create logins for your host, waiter, chef, cashier and so on.
5. Use the guest website to reserve a table, join the line or place an order.

To stop the stack, press `Ctrl + C`, then run `docker compose down`. Add `-v` to also delete the database data.

### Option B: Run without Docker

**Database:** create a PostgreSQL database, then copy `.env.example` to `.env` and set `DATABASE_URL` so that the host is `localhost` instead of `postgres`, for example:

```text
DATABASE_URL=postgresql://postgres:your-password@localhost:5432/restaurant_db
```

**Backend**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head               # create all tables
python scripts/bootstrap_admin.py --email admin@example.com --password "ChooseAStrongPassword" --name "Admin"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend** (in a new terminal)

```bash
cd frontend
npm install
npm run dev
```

The frontend proxies `/api` to `http://localhost:8000` by default. To point it somewhere else, set the `API_PROXY_TARGET` environment variable.

---

## 9. Configuration

All settings live in `.env` (copy it from `.env.example`).

| Variable | Purpose | Notes |
|---|---|---|
| `APP_ENV` | `development` or `production` | Production mode enforces strict secret checks |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Credentials for the Docker database container | Required by `docker-compose.yml` |
| `DATABASE_URL` | Connection string used by the backend | Host is `postgres` inside Docker and `localhost` outside it |
| `SECRET_KEY` | Signs login tokens | In production it must be at least 32 characters and must not be a known default |
| `ALGORITHM` | JWT signing algorithm | Default `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | How long a login stays valid | Default 30 |
| `TEST_DATABASE_URL` | Optional override used in development | |
| `SUPABASE_DATABASE_URL` | Optional hosted database used in production mode | Keep it in a local `.env` only. Never commit it |
| `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` | Placeholders for a possible hosted-auth integration | Not used by the current code |

If your database password contains an `@`, write it as `%40` in the URL.

---

## 10. How the main workflows work

### 10.1 Making a reservation

1. A guest or customer submits name, party size, start time and duration (1 to 1,440 minutes, party size 1 to 100).
2. The request must carry an `Idempotency-Key`. If the same key arrives again with the same details, the original booking is returned instead of creating a second one. If the same key arrives with different details, the server answers with a conflict.
3. The start time must be in the future.
4. If a specific table was chosen, the server locks that table's row, checks it is available, big enough, and has no overlapping active booking.
5. The reservation is saved as **pending**, and a linked **waitlist entry** is created so the host sees it in the queue. A signed-in customer receives **10 loyalty points**.
6. Only admin, manager or host staff can give a reservation VIP (tier 1) or reservation (tier 2) priority. Everyone else is tier 3.

Reservation statuses: `pending`, `confirmed`, `cancelled`, `completed`.

### 10.2 The waiting line (waitlist)

Each guest in the line has a **tier**:

| Tier | Type | Who can add them |
|---|---|---|
| 1 | VIP | Admin, manager, host |
| 2 | Reservation | Admin, manager, host |
| 3 | Walk-in | Anyone (public endpoint) |

Guests are ranked with a **priority score** (lower score is served first):

```text
score = (tier x 1000) - (seconds already waited) - (party size x 5)
```

In plain terms:

- Each tier step is worth 1,000 seconds (about 16.7 minutes) of waiting. A walk-in who has waited long enough can overtake a newer higher-tier guest.
- Every second of waiting improves a guest's position.
- Larger parties get a small boost (5 seconds per person).

Staff can **seat** a guest or **remove** them. Seating checks that the table is available, big enough, free of conflicting bookings, and (for reservations) that the booking time has arrived. Adding VIP or reservation guests who are linked to a customer account awards **+20** (VIP) or **+10** (reservation) loyalty points.

Waitlist statuses: `waiting`, `seated`, `removed`.

### 10.3 Table allocation

The host (or manager or admin) can ask the system to propose tables for all active reservations that do not yet have one:

1. **Preview** (`GET /tables/allocate`): the system returns a proposal and changes nothing.
2. **Commit** (`POST /tables/allocate`): the host saves the plan. All assignments are saved together or none are; repeating the same request is harmless.

The algorithm works through bookings in time order and gives each one the **smallest available table that fits the party and is free for the whole time slot**. Bookings that only touch at the boundary (one ends at 8:00, the next starts at 8:00) are allowed. Bookings that cannot be placed are reported as unassigned.

### 10.4 Combining tables for large parties

Admins and managers record which tables are physically next to each other. For a party size, the system builds a map of connected tables, finds each connected group, adds up the seats, and reports which groups can seat the party, with the viable ones first.

### 10.5 Placing an order

1. A waiter (for a table) or a signed-in customer (from their cart) submits the items and quantities with an `Idempotency-Key`.
2. Dine-in orders must include a table.
3. For each item the server locks the menu row, confirms it exists, is **available** and has **enough stock**, then reduces the stock and adds the price to the total. Prices are always taken from the server, never from the browser.
4. One **kitchen ticket per portion** is created and routed to a station.
5. Repeating the same request with the same key returns the same order; reusing the key with different content is rejected.

### 10.6 Kitchen workflow

Stations and which categories go to them:

| Station | Menu categories |
|---|---|
| Grill | mains, grills, starters |
| Dessert | desserts |
| Drinks | drinks, beverages |
| Sides | sides |

Items in a category the system does not recognise are spread across the four stations in **round-robin** order, so no station is overloaded. The round-robin position is stored in the database, so it survives a restart.

Ticket life cycle:

```text
queued  ->  claimed  ->  processing  ->  completed
              ^              |
              +--- release --+       (a cook can hand a ticket back)
```

- Only one cook can claim a ticket.
- Only the cook who claimed it can start and complete it (managers and admins can release it).
- When the **last** ticket of an order is completed, the order becomes **ready** automatically.

### 10.7 Order status and payment

Order statuses: `placed`, `accepted`, `preparing`, `ready`, `served`, `completed`, `cancelled` (plus a few legacy values kept for compatibility).

Each status change is limited to the right roles. For example, only kitchen roles can set *preparing* and *ready*, only waiters, managers or admins can set *served* or *cancelled*, and cashiers or waiters can set *completed*.

Payment (cashier, waiter, manager or admin): choose `upi`, `card` or `cash`. If the order belongs to a customer with **100 or more points**, a discount of ₹100 per 100 points (never more than the bill) is applied and those points are used up. The order is then marked paid and completed.

> Payments are **recorded**, not processed. The project does not connect to a payment gateway.

### 10.8 Loyalty points summary

| Event | Points |
|---|---|
| Signed-in customer makes a reservation | +10 |
| Staff adds a linked customer to the queue as VIP | +20 |
| Staff adds a linked customer to the queue as reservation | +10 |
| Walk-in queue entry | 0 |
| Redeeming at payment | 100 points = ₹100 off |

---

## 11. Data structures and algorithms

A goal of this project is to show real algorithms solving real restaurant problems. The core structures are written from scratch in `backend/app/dsa/`, are covered by unit tests, and are benchmarked.

| Problem | Structure or algorithm | File | Complexity | Live API usage |
|---|---|---|---|---|
| Who is next in the waiting line? | **Min-heap priority queue** with position tracking and the priority score formula | `priority_queue.py` | push, pop, update, remove: O(log n); build: O(n) | The ranking formula is implemented identically as a database expression, so the line is always ordered from PostgreSQL |
| Which table for which booking? | **Greedy interval scheduler** with best-fit table choice and binary search for overlaps | `interval_scheduler.py` | O(R log R + T log T) plus per-booking table scans | **Used live** by `/tables/allocate` |
| Which tables can be joined? | **Undirected graph** (adjacency list) with BFS, DFS and connected components | `table_graph.py` | O(V + E) plus neighbour sorting | **Used live** by `/tables/combine` |
| Which kitchen station gets a dish? | **Linked-list FIFO queue** and a category-to-station map with round-robin fallback | `order_router.py` | enqueue, dequeue, peek: O(1) | The station map is **used live**; ticket queues are stored in the database so they survive restarts |
| Search the menu as you type | **Trie** (prefix tree) plus a hash index by category | `trie.py` | search O(k + matches) | The live endpoint uses an indexed PostgreSQL prefix query that returns the same results |
| Find orders between two dates | **AVL (self-balancing) binary search tree** with range queries | `order_history.py` | insert, search O(log n); range O(log n + m) | The live endpoint uses an indexed date-range query |

Why this split? PostgreSQL is the permanent source of truth. For the three searches that a good database index can answer directly (queue order, menu prefix, date range), the live API lets the database do the work, so that data is never out of sync across server restarts or multiple server processes. The hand-written structures remain as tested, benchmarked reference implementations. The scheduler, graph and station router run live because their logic goes beyond what a single query can express.

Run the measurements yourself:

```bash
cd backend
python benchmarks/benchmark_dsa.py
```

---

## 12. Database design

```mermaid
erDiagram
    CUSTOMERS ||--o{ RESERVATIONS : makes
    CUSTOMERS ||--o{ ORDERS : places
    CUSTOMERS ||--o{ WAITLIST_ENTRIES : "linked to"
    TABLES ||--o{ RESERVATIONS : "assigned to"
    TABLES ||--o{ ORDERS : "serves"
    TABLES ||--o{ TABLE_ADJACENCIES : "next to"
    RESERVATIONS ||--o| WAITLIST_ENTRIES : "creates"
    ORDERS ||--|{ ORDER_ITEMS : contains
    MENU_ITEMS ||--o{ ORDER_ITEMS : "ordered as"
    ORDER_ITEMS ||--o{ KITCHEN_TICKETS : "one per portion"
    STAFF ||--o{ KITCHEN_TICKETS : claims
    STAFF ||--o{ AUDIT_LOGS : "acts in"
```

| Table | What it stores |
|---|---|
| `customers` | Guest accounts, hashed passwords, loyalty points |
| `staff` | Employee accounts, role, active flag |
| `tables` | Table number, capacity, status, current guest and party size |
| `table_adjacencies` | Pairs of tables that touch (stored in canonical order, no duplicates) |
| `reservations` | Bookings with start time, duration, status, optional table, idempotency key |
| `waitlist_entries` | The line: guest, party size, tier, join time, status, seated table |
| `menu_items` | Dishes with category, price, tags, availability, stock and low-stock threshold |
| `orders` and `order_items` | Orders and their lines, totals, payment status and method, idempotency data |
| `kitchen_tickets` | One row per portion: station, status, who claimed it and when |
| `kitchen_routing_state` | The round-robin position for unrecognised categories |
| `audit_logs` | Who did what, with role and time |

Integrity protections built into the schema:

- Check constraints: capacity, party size and durations must be greater than zero; station names must be valid; adjacency pairs are always stored low-id first
- Unique constraints: table numbers, emails, idempotency keys, one waitlist entry per reservation, one ticket per portion
- Composite and functional indexes on the columns the API filters and sorts by (reservation lookups per table, waitlist ordering, case-insensitive menu name and category, order timestamps, kitchen station queues)
- Row locks (`SELECT ... FOR UPDATE`) in the same order everywhere (table, then reservation, then waitlist) to prevent double booking and avoid deadlocks

Database changes are tracked in nine Alembic migrations (`0001_initial` through `0009_dsa_query_indexes_and_table_adjacency`), so any environment can be upgraded with `alembic upgrade head`.

---

## 13. Security

- **Passwords** are hashed with bcrypt. Plain passwords are never stored.
- **Login** returns a signed JWT (30 minutes by default). Staff and customers use separate login endpoints and the token carries the role.
- **Staff tokens are re-checked against the database** on each request: a deactivated user, or someone whose role was changed, loses access immediately.
- **Role-based access control** on every protected route (see the API reference below).
- **No public staff registration.** `POST /auth/register` always answers 403. Admins create staff accounts. The first admin is created from the command line with `scripts/bootstrap_admin.py`.
- **Rate limiting:** 10 login attempts per minute and 5 registrations per hour per IP address.
- **Production safeguards:** with `APP_ENV=production`, the app refuses to start if `SECRET_KEY` is shorter than 32 characters or is a known development value, or if the database URL still contains a development default.
- **Guest-safe public endpoints:** the public queue endpoint only reveals how many people are waiting, not who they are. Walk-in guests cannot attach themselves to a customer account or claim VIP priority.
- **Server-side pricing and stock:** prices come from the database, and stock is checked and reduced under a row lock.
- **Idempotency keys** on reservations and orders protect against double submissions and replays.
- **Audit log:** staff and table management actions are recorded with who did them.
- **CORS** allows only `http://localhost:5173` by default. Update `allow_origins` in `backend/app/main.py` when you deploy the frontend elsewhere.

---

## 14. API reference

Interactive documentation with request and response examples is generated automatically at **http://localhost:8000/docs** (Swagger UI) when the backend is running.

Summary of the endpoints:

### Authentication

| Method | Path | Access | Description |
|---|---|---|---|
| POST | `/auth/login` | Public | Staff login (email and password) |
| POST | `/auth/customer/register` | Public | Create a customer account |
| POST | `/auth/customer/login` | Public | Customer login |
| POST | `/auth/register` | Blocked | Always returns 403 |

### Tables and floor

| Method | Path | Access | Description |
|---|---|---|---|
| GET | `/tables/` and `/tables/{id}` | Public | List or view tables |
| POST | `/tables/` | Admin | Create a table |
| PUT | `/tables/{id}` | Admin, manager | Edit a table |
| PATCH | `/tables/{id}/status` | Floor roles | Change table status |
| DELETE | `/tables/{id}` | Admin | Remove a table |
| GET | `/tables/allocate` | Admin, manager, host | Preview allocation proposal |
| POST | `/tables/allocate` | Admin, manager, host | Save allocation plan |
| POST, DELETE | `/tables/{id}/adjacent/{other_id}` | Admin, manager | Mark or unmark two tables as neighbours |
| GET | `/tables/combine?party_size=N` | Admin, manager, waiter, host | Table groups that can seat a party |

### Waitlist

| Method | Path | Access | Description |
|---|---|---|---|
| POST | `/waitlist/join` | Public | Walk-in joins the line |
| POST | `/waitlist/staff-join` | Admin, manager, host | Add a VIP or reservation guest |
| GET | `/waitlist/status` | Public | Number of parties waiting |
| GET | `/waitlist/` | Any staff | Full ordered queue with scores |
| POST | `/waitlist/{id}/seat` | Admin, manager, waiter, host | Seat a party at a table |
| POST | `/waitlist/{id}/remove` | Admin, manager, waiter, host | Remove a party from the line |

### Reservations

| Method | Path | Access | Description |
|---|---|---|---|
| POST | `/reservations/` | Public (needs `Idempotency-Key` header) | Create a reservation |
| GET | `/reservations/` | Any staff | List all reservations |
| GET | `/reservations/mine` | Customer | My reservations |
| GET | `/reservations/account` | Customer | My profile and points |
| PATCH | `/reservations/{id}/status` | Admin, manager, waiter, host | Confirm, cancel or complete |

### Menu

| Method | Path | Access | Description |
|---|---|---|---|
| GET | `/menu/`, `/menu/{id}` | Public | Browse the menu |
| GET | `/menu/search?q=` | Public | Prefix search by dish name |
| GET | `/menu/category/{tag}` | Public | Dishes in a category |
| POST, PUT | `/menu/`, `/menu/{id}` | Admin, manager | Create or edit (price changes are admin only) |
| PATCH | `/menu/{id}/availability` | Admin, manager, chef, kitchen staff | Switch a dish on or off |
| DELETE | `/menu/{id}` | Admin | Delete a dish |

### Orders and payment

| Method | Path | Access | Description |
|---|---|---|---|
| POST | `/orders/` | Admin, manager, waiter | Staff creates an order (needs `Idempotency-Key`) |
| POST | `/orders/customer` | Customer | Customer places an order (needs `Idempotency-Key`) |
| GET | `/orders/mine` | Customer | My orders |
| GET | `/orders/active` | Staff | Orders not yet completed or cancelled |
| GET | `/orders/history?from=&to=` | Any staff | Orders in a date range |
| GET | `/orders/{id}` | Any staff | One order |
| PUT | `/orders/{id}/status` | Role-specific | Move an order through its stages |
| POST | `/orders/{id}/payment` | Cashier, waiter, manager, admin | Record payment and apply loyalty discount |

### Kitchen

| Method | Path | Access | Description |
|---|---|---|---|
| GET | `/kitchen/{station}` | Admin, manager, chef, kitchen staff | Active tickets at `grill`, `dessert`, `drinks` or `sides` |
| POST | `/kitchen/tickets/{id}/claim` | Same | Take a ticket |
| POST | `/kitchen/tickets/{id}/start` | Same | Start cooking |
| POST | `/kitchen/tickets/{id}/complete` | Same | Finish the ticket |
| POST | `/kitchen/tickets/{id}/release` | Claimant, manager, admin | Hand the ticket back |

### Staff and administration

| Method | Path | Access | Description |
|---|---|---|---|
| GET, POST | `/staff/` | Admin | List or create employees |
| GET, PUT, DELETE | `/staff/{id}` | Admin | View, edit or remove an employee |
| GET | `/staff/customers` | Admin, manager, host | Customer list for linking guests to accounts |
| GET | `/admin/summary` | Admin | Today's numbers and operational counts |
| GET | `/admin/reports` | Admin | 7-day bookings, orders and revenue |
| GET | `/admin/audit` | Admin | Latest 100 audit entries |
| GET | `/admin/customers` | Admin | All customers |
| POST | `/admin/tables` | Admin | Create a table (audited) |
| POST | `/admin/tables/allocate` | Admin | Seat any guest at any free table directly (audited) |
| GET | `/` | Public | Health check |

---

## 15. Frontend pages

| Page | Route | Who sees it |
|---|---|---|
| Landing page | `/` | Everyone |
| Login (customer or staff) | `/login` | Everyone |
| Staff workspace picker | `/staff/select` | Everyone (login still required) |
| Customer home | `/customer` | Everyone |
| Menu and cart | `/customer/menu`, `/menu` | Everyone (ordering needs a customer login) |
| Reserve a table | `/customer/reservation` | Everyone |
| Public queue view | `/customer/waitlist` | Everyone |
| My dining account | `/customer/account` | Signed-in customer |
| Staff home (role-specific dashboard) | `/staff` | Staff: host, waiter, cashier or manager view |
| Admin dashboard | `/admin` | Admin |
| Employee accounts | `/staff/manage` | Admin |
| Kitchen dashboard (station queues) | `/kitchen` | Chef, kitchen staff, manager, admin |
| Waitlist | `/waitlist` | Staff (not kitchen-only) |
| Table map and allocator | `/tables` | Staff (not kitchen-only) |
| Staff reservations | `/reservation` | Staff (not kitchen-only or waiter) |
| Order history | `/history` | Staff (not kitchen-only) |

The staff home page shows a different dashboard depending on the role: **Host / Floor Manager**, **Waiter Dashboard**, **Kitchen Dashboard**, **Cashier Station** or the general **Operations Overview**. The kitchen view refreshes itself every 20 seconds.

The menu search box waits 300 ms after you stop typing before it queries the server, which keeps the app responsive and the server calm.

> The browser hides pages a role should not see, but the real protection is on the server: every endpoint checks the role again.

---

## 16. Testing and benchmarks

**Run the automated tests** (no database setup needed, they use an in-memory database):

```bash
cd backend
python -m pytest -q
```

The suite contains 200+ tests covering:

- each data structure (heap, trie, scheduler, graph, queue router, AVL tree)
- reservations and table allocation, including conflicts
- the waitlist and kitchen workflow
- security: login, roles, rate limits, production secret checks
- API behaviour for key routes

**End-to-end script:** `e2e_tests.py` in the project root is an optional script for exercising a running system.

**Benchmarks:** `python backend/benchmarks/benchmark_dsa.py` produces fresh before/after timing measurements for the algorithms and query shapes. Results come from your own machine; none are claimed in this document.

---

## 17. Known limitations and future work

Being clear about what the project does not do (yet):

- **No sample data.** Tables and menu items must be added through the admin dashboard or the API.
- **Payments are recorded, not processed.** There is no payment gateway integration.
- **The rate limiter is in memory** and is per server process. With several server replicas, use a shared store such as Redis.
- **Docker Compose is a development setup** (hot reload, source folders mounted into the containers). A production deployment would use built frontend files behind a web server, no reload mode and a proper secrets store.
- **CORS** is restricted to `http://localhost:5173` until you change it.
- **Orders are dine-in focused.** Dine-in orders require a table.
- **No email or SMS notifications.**
- The Supabase API keys in `.env.example` are placeholders for a possible future hosted-auth integration and are not used by the current code.

Ideas for future work:

- Real-time updates (WebSockets) for the kitchen and floor screens
- Payment gateway integration (UPI, card)
- Reservation reminders by SMS or email
- Sales analytics: popular dishes, peak hours, average wait time
- Inventory tracking with automatic reorder alerts
- Redis-backed rate limiting and caching
- Production deployment guide (CI/CD, HTTPS, managed PostgreSQL)

---

## 18. Glossary

| Term | Meaning |
|---|---|
| **API** | The set of "doors" the website uses to talk to the server. |
| **Backend** | The server part of the app that holds the rules and talks to the database. |
| **Frontend** | The part you see and click in the browser. |
| **Database** | The organised storage where everything (bookings, orders, accounts) is kept permanently. |
| **JWT** | A signed digital pass the server gives you when you log in, proving who you are. |
| **Role** | A job title (host, waiter and so on) that decides what you are allowed to do. |
| **Waitlist** | The waiting line of guests without a table. |
| **Priority queue** | A line where urgency, not just arrival time, decides who goes first. |
| **Idempotency key** | A unique ticket number on a request so that sending it twice has the same effect as sending it once. |
| **Migration** | A versioned, repeatable change to the database structure. |
| **Docker** | A tool that packages the app and its database so they run the same way on any computer. |
| **Station** | A section of the kitchen (grill, dessert, drinks, sides). |
| **Ticket** | One portion of one dish waiting to be prepared. |
| **Audit log** | A history of who did which important action. |

---

## 19. Author

Built by **Anil** ([@Aneelchoudhari](https://github.com/Aneelchoudhari)), B.E. Electrical and Electronics Engineering student at Ramaiah Institute of Technology, as a full-stack project focused on backend engineering and practical data structures and algorithms.

If you find this project useful, consider giving the repository a star.
