from fastapi import FastAPI
import uvicorn

from app.api.user_info import router as monobank_router  

app = FastAPI()

app.include_router(monobank_router, prefix="/monobank", tags=["monobank"])

if __name__ == '__main__':
    uvicorn.run("main:app", reload=True)