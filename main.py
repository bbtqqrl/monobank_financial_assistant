from fastapi import FastAPI
from api.webhook import router as webhook_router

app = FastAPI()

app.include_router(webhook_router)

@app.get("/")
def root():
    return {"status": "running"}