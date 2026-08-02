from fastapi import FastAPI
from pydantic import BaseModel
from runtime.genius_runtime import GeniusRuntime
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI()

runtime = GeniusRuntime()


class ChatRequest(BaseModel):
    message: str


@app.on_event("startup")
async def startup():
    await runtime.initialize()


@app.post("/chat")
async def chat(req: ChatRequest):
    result = await runtime.run(req.message)

    return {
        "response": result["response"],
        "model": result.get("model", "unknown"),
        "memory_used": result.get("memory_used", 0)
    }


@app.on_event("shutdown")
async def shutdown():
    await runtime.shutdown()
