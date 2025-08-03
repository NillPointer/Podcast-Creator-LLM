from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app.api import router
from app.config.settings import settings
from app.logger import setup_logger
import logging

# Setup logging
logger = setup_logger('podcast_creator')

# Configure FastAPI to reduce log noise
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

app = FastAPI(
    title="Podcast Creator API",
    description="Convert PDF content into 2-host podcasts using LLM and TTS",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1")

@app.get("/")
async def root():
    with open("static/index.html", "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content, media_type="text/html")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}