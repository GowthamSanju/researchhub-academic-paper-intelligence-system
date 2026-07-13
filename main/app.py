"""FastAPI application."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .service.database_service import initialize_database

from .routes import router
from .service.multimodal_service import get_service

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Loads existing index from PostgreSQL on application startup.
    """
    # Startup: Load existing index
    logger.info("Application startup: Loading existing index from PostgreSQL...")
    try:
        initialize_database()
        service = get_service()
        service.initialize()  # This will attempt to load existing index
        if service.is_initialized():
            logger.info("✅ Successfully loaded existing index on startup")
        else:
            logger.info("ℹ️  No existing index found (this is normal for first run)")
    except Exception as e:
        logger.warning(f"Could not load existing index on startup: {e}")
        logger.info("Application will continue - index will be created on first document upload")
    
    yield
    
    # Shutdown: Cleanup if needed
    logger.info("Application shutdown: Cleaning up...")


app = FastAPI(
    title="ResearchHub – Academic Paper Intelligence System",
    description="API for unified multi-modal retrieval across text, tables, and images",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router, prefix="/api/v1", tags=["api"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "ResearchHub – Academic Paper Intelligence System",
        "version": "1.0.0",
        "docs": "/docs"
    }


def main():
    """Entry point for running the application."""
    import uvicorn
    from dotenv import load_dotenv
    
    load_dotenv()
    logger.info("Starting ResearchHub – Academic Paper Intelligence System server...")
    
    uvicorn.run(
        "main.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

