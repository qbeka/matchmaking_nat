from fastapi import FastAPI

from app.api.match import router as match_router

app = FastAPI()

app.include_router(match_router, prefix="/api")


@app.get("/health-check")
async def health_check():
    return {"status": "ok"}
