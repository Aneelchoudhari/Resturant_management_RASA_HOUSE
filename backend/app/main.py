from fastapi import FastAPI

app = FastAPI(title="Restaurant Management System")


@app.get("/")
def health_check():
    return {"status": "ok"}
