from fastapi import FastAPI
from app.routers import tables, menu, staff

app = FastAPI(title="Restaurant Management System")

app.include_router(tables.router)
app.include_router(menu.router)
app.include_router(staff.router)


@app.get("/")
def health_check():
    return {"status": "ok"}
