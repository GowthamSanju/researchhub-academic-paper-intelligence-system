"""API server entry point."""
import logging
import uvicorn
from dotenv import load_dotenv

from main.app import app

# Load environment variables from .env file
load_dotenv()

# Configure logging (app.py also configures it, but this ensures it's set up)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.info("Starting Unified Multi-Modal RAG API server...")
    uvicorn.run(
        "main.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

