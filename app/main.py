from fastapi import FastAPI

app = FastAPI()


@app.get("/health-check")
async def health_check():
    return {"status": "ok"}
