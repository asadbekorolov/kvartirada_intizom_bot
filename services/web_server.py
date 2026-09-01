from datetime import datetime, timezone
from aiohttp import web
import logging

logger = logging.getLogger("kvartira_bot.web")


async def health_check_handler(request: web.Request) -> web.Response:
    now_iso = datetime.now(timezone.utc).isoformat()
    return web.json_response({
        "status": "ok",
        "service": "kvartira_bot",
        "timestamp": now_iso
    }, status=200)


def create_web_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", health_check_handler)
    app.router.add_get("/health", health_check_handler)
    return app


async def start_web_server(host: str = "0.0.0.0", port: int = 8080) -> web.AppRunner:
    app = create_web_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info(f"Keep-alive HTTP health check server started at http://{host}:{port}/health")
    return runner
