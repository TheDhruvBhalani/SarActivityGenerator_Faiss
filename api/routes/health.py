"""
Health Check Endpoints
"""
from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/")
async def root():
    """Root endpoint"""
    return {"service": "SAR API", "version": "3.0.0", "status": "running"}


@router.get("/api/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "services": {
            "database": "available",
            "ragpipeline": "loaded",
            "llmengine": "loaded"
        }
    }
