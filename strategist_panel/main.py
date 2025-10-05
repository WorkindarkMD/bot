import asyncio
import logging
from aiohttp import web
from pathlib import Path

# --- Configuration ---
HOST = "localhost"
PORT = 8080  # Port for the web interface
LOG_LEVEL = logging.INFO
UI_DIR = Path(__file__).parent / "ui"

# --- Logging Setup ---
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("StrategistPanelWebServer")

async def index(request):
    """Serves the main index.html file."""
    return web.FileResponse(UI_DIR / 'index.html')

async def main():
    """
    Sets up and runs the aiohttp web server to serve the Strategist Panel UI.
    """
    app = web.Application()

    # Add routes
    # The main route serves the HTML file
    app.router.add_get('/', index)

    # This route serves all other static files (like CSS and JS) from the 'ui' directory
    app.router.add_static('/', path=UI_DIR, name='ui')

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)

    logger.info(f"Strategist Panel web server starting...")
    logger.info(f"Access the panel at http://{HOST}:{PORT}")

    await site.start()

    # Keep the server running until it's manually stopped
    try:
        while True:
            await asyncio.sleep(3600) # Sleep for a long time
    except asyncio.CancelledError:
        logger.info("Server is shutting down.")
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user.")