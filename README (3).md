# Restaurant Management System

A full-stack restaurant management application built with FastAPI, PostgreSQL, React, and Vite. The backend includes self-implemented data structures and algorithms for waitlist prioritization, reservation allocation, menu search, kitchen routing, order history, and table grouping.

## Features

### Customer experience

- Browse and search the menu
- Create reservations
- View the current waitlist in read-only mode
- Create a customer account with saved identity and reservation history
- Earn 10 loyalty points for each signed-in reservation
- Build a cart and place dine-in or takeaway orders
- Add order quantities and special instructions
- Track order status and payment status from the customer account
- Customer-focused navigation and landing page

### Staff experience

- Staff/admin JWT authentication
- Waitlist management with priority ordering
- Table map and allocation tools
- Kitchen station queues
- Order history and management views
- Staff-focused navigation and operations dashboard
- Backend-enforced roles for admin, manager, waiter, chef, cashier, and inventory staff
- Staff order status transitions and payment completion
- Menu availability, descriptions, and images metadata
- Table states including available, occupied, reserved, and cleaning

## Stack

- **Frontend:** React 18, React Router, Vite
- **Backend:** Python, FastAPI, SQLAlchemy, Alembic
- **Database:** PostgreSQL 15
- **Authentication:** OAuth2 form login with JWT bearer tokens and customer/staff/admin roles
- **Testing:** Pytest
- **Runtime:** Docker Compose

## Run With Docker

Prerequisites: Docker Desktop with Docker Compose enabled.

```powershell
docker compose up --build
```

Open:

- Frontend: http://localhost:5173
- Backend health check: http://localhost:8000
- Swagger API docs: http://localhost:8000/docs

Stop the services with:

```powershell
docker compose down
```

The PostgreSQL data is stored in the `postgres_data` Docker volume. To remove the database volume as well:

```powershell
docker compose down -v
```

## Local Development Without Docker

### Backend

From `backend/`, install the dependencies and start FastAPI:

```powershell
python -m pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000
```

If PostgreSQL is unavailable, the application can fall back to SQLite for local development and tests. Set `DATABASE_URL` explicitly when using another database.

### Frontend

From `frontend/`:

```powershell
npm install
npm run dev
```

The Vite development server runs at http://localhost:5173.

## Authentication Flow

The application supports separate customer and staff accounts. Customers can browse publicly, or create an account to save their name on reservations, view reservation history, and earn loyalty points. Staff and admin accounts access the operations dashboard.

Staff accounts are never self-registered. An administrator creates an employee account from the admin staff-management screen or the protected `POST /staff/` endpoint, then securely gives the employee their provisioned email and temporary password. The public `POST /auth/register` endpoint is disabled and returns `403`.

The current runtime uses PostgreSQL plus the application JWT layer. Supabase placeholders are included in `.env.example`, but a hosted Supabase switch requires the project URL, anon key, and backend-only service-role key to be configured first. Never put the service-role key in frontend code.

### Connect the application to Supabase Postgres

The Supabase dashboard URL and API keys do not contain the PostgreSQL connection string. Copy the **Session pooler URI** from Supabase **Connect** and place it in a local root `.env` file (which is gitignored):

```env
SUPABASE_DATABASE_URL=postgresql://postgres.<project-ref>:<database-password>@<pooler-host>:5432/postgres
SECRET_KEY=<long-random-application-secret>
```

Then run the migrations:

```powershell
docker compose down
docker compose up --build -d
```

The backend startup runs `alembic upgrade head`, creating `public.staff`, `public.customers`, `public.orders`, and the other application tables in Supabase Postgres. The current application login uses these application tables; a user created only under Supabase Authentication is not automatically an application staff user.

To create or promote the first application admin after the migration:

```powershell
cd backend
python scripts/bootstrap_admin.py --email admin@example.com --password "choose-a-password" --name "Restaurant Admin"
```

After that, the admin can create employee accounts from `/staff/manage`. Public staff registration is disabled.

Register an account:

```powershell
curl -X POST http://localhost:8000/auth/register `
  -H "Content-Type: application/json" `
  -d '{"name":"Restaurant Staff","email":"staff@example.com","password":"change-me","role":"staff"}'
```

Then use **Staff Login** in the frontend. The JWT role controls the interface:

- `staff` and `admin` users are sent to the staff dashboard.
- `customer` users are sent to their customer account and reservation history.
- Guests without an account are sent to the public customer experience.
- Staff-only routes redirect unauthorized users to the customer area.

Customer registration is available from the **Customer Login** screen. Customer reservations are available through `POST /reservations/`, account details through `GET /reservations/account`, and reservation history through `GET /reservations/mine`.

## Testing

Run the backend test suite from `backend/`:

```powershell
python -m pytest -q
```

Build the frontend from `frontend/`:

```powershell
npm run build
```

## DSA Modules

| Module | Implementation | Purpose |
| --- | --- | --- |
| Waitlist | Custom min-heap priority queue | Orders guests by priority and wait time |
| Table allocation | Greedy interval scheduler | Assigns tables while avoiding reservation conflicts |
| Menu search | Trie and category index | Supports prefix and category searches |
| Kitchen routing | Station queues | Routes order items to kitchen stations |
| Order history | Sorted/BST-style index | Supports order lookup and range queries |
| Table grouping | Graph traversal | Finds connected table combinations |

## Project Structure

```text
backend/app/        FastAPI application, routers, models, schemas, DSA modules
backend/tests/      Backend and DSA tests
frontend/src/       React application, role-based routes, pages, and styles
docker-compose.yml  PostgreSQL, backend, and frontend services
```
