from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from core.api_routes import auth_routes, seed_routes, credit_routes, harness_routes, agi_routes, space_routes
from core.space_service import space_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动自动同步
    space_service.start_auto_sync(interval=300)
    # 启动健康检查
    space_service.start_health_check(interval=60)
    yield
    # 停止线程
    space_service.stop_auto_sync()
    space_service.stop_health_check()

app = FastAPI(title="SASES Full Web Service", version="0.8.2", lifespan=lifespan)

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
