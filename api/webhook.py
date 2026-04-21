from fastapi import APIRouter, Request

router = APIRouter()

fake_db = []

@router.post("/mono-webhook")
async def mono_webhook(request: Request):
    payload = await request.json()

    tx = {
        "amount": payload.get("data", {}).get("statementItem", {}).get("amount"),
        "description": payload.get("data", {}).get("statementItem", {}).get("description"),
    }

    fake_db.append(tx)

    print("DB:", fake_db)

    return {"ok": True}