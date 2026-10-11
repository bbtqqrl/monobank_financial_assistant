import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)

import sentry_sdk

from app.core.config import SENTRY_DSN, SENTRY_ENVIRONMENT, SENTRY_TRACES_SAMPLE_RATE

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENVIRONMENT,
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,
        max_request_body_size="never",
        include_local_variables=False,
    )

from app.api.accounts import router as accounts_router
from app.api.auth import router as auth_router
from app.api.budgets import router as budgets_router
from app.api.categories import router as categories_router
from app.api.merchant_mappings import router as merchant_mappings_router
from app.api.transactions import router as transactions_router
from app.api.user_connect import router as monobank_router
from app.api.webhook import router as webhook_router
from app.services.categorization_sweeper import run_sweeper_forever

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    sweeper = asyncio.create_task(run_sweeper_forever())
    yield
    sweeper.cancel()
    with suppress(asyncio.CancelledError):
        await sweeper


app = FastAPI(lifespan=lifespan)

app.include_router(auth_router)
app.include_router(webhook_router)
app.include_router(monobank_router)
app.include_router(accounts_router)
app.include_router(transactions_router)
app.include_router(merchant_mappings_router)
app.include_router(budgets_router)
app.include_router(categories_router)


if __name__ == '__main__':
    uvicorn.run("main:app", reload=True)