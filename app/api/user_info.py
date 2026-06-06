from fastapi import APIRouter, HTTPException

from app.services.monobank import MonobankService

router = APIRouter()

@router.post("/check-token")
async def check_token(data: dict):
    try:
        result = await MonobankService().get_client_info(data["token"])
        return result
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid token")