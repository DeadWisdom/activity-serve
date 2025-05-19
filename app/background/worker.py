import asyncio
import structlog
from threading import Thread
from typing import Optional

from app.services.activity import get_activity_bus

logger = structlog.get_logger(__name__)

# Global variable to control the background worker
worker_running = False
worker_thread: Optional[Thread] = None


async def background_worker_loop():
    """Background loop that processes activities from the bus."""
    global worker_running
    bus = get_activity_bus()
    
    logger.info("Background worker started")
    
    while worker_running:
        try:
            # Process the next activity from the bus
            processed = await bus.process_next()
            
            if not processed:
                # If no activity was processed, sleep briefly
                await asyncio.sleep(0.1)
        except Exception as e:
            logger.exception("Error in background worker", error=str(e))
            # Sleep briefly to avoid busy-waiting in case of recurring errors
            await asyncio.sleep(1)


def _run_worker_thread():
    """Run the worker loop in a new event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    loop.run_until_complete(background_worker_loop())
    loop.close()


def start_background_worker():
    """Start the background worker in a separate thread."""
    global worker_running, worker_thread
    
    if worker_running:
        logger.warning("Background worker already running")
        return
    
    worker_running = True
    worker_thread = Thread(target=_run_worker_thread, daemon=True)
    worker_thread.start()
    
    logger.info("Background worker thread started")


def stop_background_worker():
    """Stop the background worker thread."""
    global worker_running, worker_thread
    
    if not worker_running:
        logger.warning("Background worker not running")
        return
    
    worker_running = False
    
    if worker_thread:
        worker_thread.join(timeout=5)
        worker_thread = None
    
    logger.info("Background worker stopped")