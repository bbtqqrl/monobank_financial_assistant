import asyncio
from contextlib import asynccontextmanager, suppress

from asyncpg.exceptions import DataError as AsyncpgDataError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError
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
from app.api.analytics import router as analytics_router
from app.api.assistant import router as assistant_router
from app.api.auth import router as auth_router
from app.api.budgets import router as budgets_router
from app.api.categories import router as categories_router
from app.api.devices import router as devices_router
from app.api.merchant_mappings import router as merchant_mappings_router
from app.api.notifications import router as notifications_router
from app.api.places import router as places_router
from app.api.recurring import router as recurring_router
from app.api.transactions import router as transactions_router
from app.api.user_connect import router as monobank_router
from app.api.webhook import router as webhook_router
from app.services.errors import ServiceError
from app.services.categorization_sweeper import run_sweeper_forever
from app.services.notifications import run_notifier_forever

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks = [asyncio.create_task(run_sweeper_forever()), asyncio.create_task(run_notifier_forever())]
    yield
    for task in tasks:
        task.cancel()
    for task in tasks:
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(lifespan=lifespan)


@app.exception_handler(ServiceError)
async def service_error(request: Request, exc: ServiceError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(DBAPIError)
async def query_argument_error(request: Request, exc: DBAPIError):
    # A value the driver can't even encode for its column - e.g. an id past
    # int32 in a path or query param - is bad input, not a server error.
    cause = exc.orig.__cause__ if exc.orig is not None else None
    if isinstance(cause, AsyncpgDataError) and str(cause).startswith("invalid input for query argument"):
        return JSONResponse(status_code=422, content={"detail": "Invalid input value"})
    raise exc

app.include_router(auth_router)
app.include_router(webhook_router)
app.include_router(monobank_router)
app.include_router(accounts_router)
app.include_router(transactions_router)
app.include_router(merchant_mappings_router)
app.include_router(budgets_router)
app.include_router(categories_router)
app.include_router(analytics_router)
app.include_router(assistant_router)
app.include_router(places_router)
app.include_router(recurring_router)
app.include_router(notifications_router)
app.include_router(devices_router)


if __name__ == '__main__':
    uvicorn.run("main:app", reload=True)