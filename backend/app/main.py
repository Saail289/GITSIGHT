"""
Main FastAPI application entry point.
Configures the app, middleware, and routes.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import routes
from app.config.settings import settings

# Validate settings on startup
settings.validate()

# Create FastAPI app
app = FastAPI(
    title="GitHub RAG Assistant API",
    description="API for answering questions about GitHub repositories using RAG",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(routes.router, prefix="/api")

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "GitHub RAG Assistant API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/api/health",
            "ingest": "/api/ingest",
            "query": "/api/query",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Auto-reload on code changes
    )
