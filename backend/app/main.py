from fastapi import FastAPI
from app.routers import tables, menu, staff, waitlist, allocation, graph
from app.routers.orders import router as orders_router, kitchen_router

app = FastAPI(title="Restaurant Management System")

app.include_router(tables.router)
app.include_router(menu.router)
app.include_router(staff.router)
app.include_router(waitlist.router)
app.include_router(allocation.router)
app.include_router(graph.router)
app.include_router(orders_router)
app.include_router(kitchen_router)


@app.get("/")
def health_check():
    return {"status": "ok"}
