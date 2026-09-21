from fastapi import FastAPI
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
from app.api.accounts import router as accounts_router
from app.api.auth import router as auth_router
from app.api.transactions import router as transactions_router
from app.api.user_connect import router as monobank_router
from app.api.webhook import router as webhook_router
app = FastAPI()

app.include_router(auth_router)
app.include_router(webhook_router)
app.include_router(monobank_router)
app.include_router(accounts_router)
app.include_router(transactions_router)

if __name__ == '__main__':
    uvicorn.run("main:app", reload=True)