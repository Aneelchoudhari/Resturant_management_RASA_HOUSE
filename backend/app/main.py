from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import tables, menu, staff, waitlist, allocation, graph
from app.routers.orders import router as orders_router, kitchen_router
from app.routers.auth_router import router as auth_router
from app.routers.reservations import router as reservations_router
from app.routers.admin import router as admin_router

app = FastAPI(title="Restaurant Management System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(allocation.router)   # /tables/allocate — must be before tables /{table_id}
app.include_router(graph.router)         # /tables/combine  — must be before tables /{table_id}
app.include_router(tables.router)
app.include_router(menu.router)
app.include_router(staff.router)
app.include_router(waitlist.router)
app.include_router(orders_router)
app.include_router(kitchen_router)
app.include_router(auth_router)
app.include_router(reservations_router)
app.include_router(admin_router)


@app.get("/")
def health_check():
    return {"status": "ok"}
