from fastapi import FastAPI
import asyncio
from api.v1.router import router
from workers.message_worker import message_worker


app = FastAPI(
    title="Telegram Service",
)

app.include_router(
    router,
    prefix="/api/v1",
)

@app.on_event("startup")
async def startup():
    for worker_id in range(3):
        asyncio.create_task(
            message_worker(worker_id)
        )
