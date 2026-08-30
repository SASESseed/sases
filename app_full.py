from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from core.api_routes import auth_routes, seed_routes, credit_routes, harness_routes, agi_routes, space_routes
from core.space_service import space_service
from core import config
from core.discovery import NodeDiscovery

discovery = NodeDiscovery(on_peer_discovered=lambda peer_url: space_service.sync_from_peer(peer_url))

@asynccontextmanager
async def lifespan(app: FastAPI):
    space_service.start_auto_sync(interval=300)
    space_service.start_health_check(interval=60)
    if config.ENABLE_MDNS:
        discovery.start()
    yield
    if config.ENABLE_MDNS:
        discovery.stop()
    space_service.stop_auto_sync()
    space_service.stop_health_check()

app = FastAPI(title="SASES Full Web Service", version="0.12.0", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth_routes.router)
app.include_router(seed_routes.router)
app.include_router(credit_routes.router)
app.include_router(harness_routes.router)
app.include_router(agi_routes.router)
app.include_router(space_routes.router)

@app.get("/")
async def root():
    return {"message": "SASES Full Web Service is running. Visit /static/index.html for UI."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
