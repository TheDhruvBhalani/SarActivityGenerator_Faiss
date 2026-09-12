"""
SAR Generation System - Main Entry Point

Usage:
    uvicorn main:app --reload --port 8000

Or run directly:
    python main.py
"""
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI

from config.settings import Config, APIConfig
from api.middleware import setup_middleware
from api.auth import AuthManager
from api.routes import sar_router, feedback_router, health_router
from database.schema import initialize_main_database, initialize_track_c_database


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup/shutdown"""
    # Startup
    print("="*60)
    print("SAR GENERATION SYSTEM - STARTING")
    print("="*60)

    # Ensure directories exist
    Config.ensure_directories()
    print("Directories initialized")

    # Initialize databases
    initialize_main_database()
    initialize_track_c_database()
    print("Databases initialized")

    print("\nAvailable endpoints:")
    print("  GET  /                        - Root")
    print("  GET  /api/health              - Health check")
    print("  POST /api/v1/auth/login       - Login")
    print("  POST /api/v1/generate-sar     - Generate SAR")
    print("  POST /api/v1/sar/{id}/approve - Approve SAR")
    print("  GET  /api/v1/logic-audit-trail/{id} - Get audit trail")
    print("  GET  /api/v1/learning/metrics - Learning metrics")
    print("  GET  /api/v1/learning/patterns - Learned patterns")
    print("  GET  /api/v1/learning/prompt  - Current prompt")

    print("\n" + "="*60)
    print("SYSTEM READY")
    print("="*60)

    yield  # App runs here

    # Shutdown
    print("Shutting down...")


# Create FastAPI app with lifespan
app = FastAPI(
    title="SAR Generation API",
    description="Suspicious Activity Report Generation System with AI",
    version="3.0.0",
    lifespan=lifespan
)

# Setup middleware
setup_middleware(app)

# Initialize authentication
AuthManager.init_passwords()

# Include routers
app.include_router(health_router)
app.include_router(sar_router)
app.include_router(feedback_router)


if __name__ == "__main__":
    import uvicorn

    # Run server (databases initialized via lifespan)
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
