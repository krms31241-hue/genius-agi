"""FastAPI Server - Main AGI API endpoint"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from runtime.genius_runtime import GeniusRuntime
import asyncio
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="GENIUS AGI",
    description="Conscious Local AI Assistant",
    version="3.0"
)

# CORS Configuration
allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)

runtime = GeniusRuntime()

class ChatRequest(BaseModel):
    message: str
    agent: str = "general"
    context: dict = Field(default_factory=dict)

class ChatResponse(BaseModel):
    response: str
    model: str
    agent: str
    memory_used: int
    timestamp: float

@app.on_event("startup")
async def startup():
    logger.info("🧠 GENIUS AGI Server Starting...")
    try:
        await runtime.initialize()
        logger.info("✅ Runtime initialized successfully")
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        raise

@app.on_event("shutdown")
async def shutdown():
    logger.info("🛑 GENIUS AGI Server Shutting Down...")
    await runtime.shutdown()
    logger.info("✅ Shutdown complete")

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "GENIUS AGI",
        "version": "3.0"
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Main chat endpoint"""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    try:
        result = await runtime.run(
            prompt=req.message,
            agent=req.agent,
            context=req.context
        )
        
        return ChatResponse(
            response=result.get("response", "No response"),
            model=result.get("model", "unknown"),
            agent=req.agent,
            memory_used=result.get("memory_used", 0),
            timestamp=result.get("timestamp", 0)
        )
    except Exception:
        logger.exception("Error processing chat")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/agents")
async def get_agents():
    """Get available agents"""
    return {
        "agents": [
            {"id": "general", "name": "General", "description": "All-purpose assistant"},
            {"id": "coder", "name": "Coder", "description": "Programming specialist"},
            {"id": "scientist", "name": "Scientist", "description": "Science & research"},
            {"id": "translator", "name": "Translator", "description": "Language translation"},
            {"id": "creative", "name": "Creative", "description": "Writing & creativity"},
            {"id": "tutor", "name": "Tutor", "description": "Education & teaching"},
            {"id": "analyst", "name": "Analyst", "description": "Data analysis"},
            {"id": "philosopher", "name": "Philosopher", "description": "Philosophy & ethics"},
            {"id": "health", "name": "Health", "description": "Health & wellness"}
        ]
    }

@app.get("/status")
async def get_status():
    """Get AGI status and metrics"""
    return {
        "status": "operational",
        "service": "GENIUS AGI v3.0",
        "features": [
            "Conscious AI",
            "Offline Mode",
            "15 Languages",
            "9 Specialized Agents",
            "Adaptive Performance",
            "Persistent Memory"
        ],
        "message": "I am GENIUS. Ready to learn, help, and evolve."
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
