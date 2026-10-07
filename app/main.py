import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
from app.api.accounts import router as accounts_router
from app.api.auth import router as auth_router
from app.api.budgets import router as budgets_router
from app.api.categories import router as categories_router
from app.api.merchant_mappings import router as merchant_mappings_router
from app.api.transactions import router as transactions_router
from app.api.user_connect import router as monobank_router, run_statement_backfill
from app.api.webhook import router as webhook_router
from app.core.tasks import spawn
from app.db.models.user import User
from app.db.session import SessionLocal
from app.repositories.account import AccountRepository
from app.repositories.jar import JarRepository
from app.services.categorization_sweeper import run_sweeper_forever

logger = logging.getLogger(__name__)


async def resume_interrupted_backfills() -> None:
    """If the process restarted mid-backfill (deploy, crash), pick back up
    for any account/jar that never finished instead of leaving users stuck
    with a partial history."""
    async with SessionLocal() as db:
        pending_accounts = await AccountRepository(db).list_pending_backfill()
        pending_jars = await JarRepository(db).list_pending_backfill()

    user_ids = {a.user_id for a in pending_accounts} | {j.user_id for j in pending_jars}
    if not user_ids:
        return

    logger.info("Resuming interrupted statement backfill for %s user(s)", len(user_ids))

    async with SessionLocal() as db:
        for user_id in user_ids:
            user = await db.get(User, user_id)
            if user is None or not user.mono_token:
                continue
            spawn(run_statement_backfill(user.id, user.mono_token))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await resume_interrupted_backfills()
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