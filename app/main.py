from fastapi import FastAPI
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
from app.api.user_connect import router as monobank_router  
from app.api.webhook import router as webhook_router
app = FastAPI()

app.include_router(webhook_router)
app.include_router(monobank_router)

if __name__ == '__main__':
    uvicorn.run("main:app", reload=True)