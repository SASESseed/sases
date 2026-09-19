# core/bootstrap.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from contextlib import asynccontextmanager
import asyncio

from .db import init_db, db_cursor
from .services import memory_service
from .services import debug_service
from .services import rescue_service
from .services import swarm_service
from .services import executor_service
from .services import cleanup_service
from .services import pattern_service
from .services import pattern_service
from . import backup_service
from .api_routes import (
    auth_routes,
    seed_routes,
    credit_routes,
    harness_routes,
    agi_routes,
    space_routes,
    group_routes,
    model_routes,
    agent_routes,
    chat_routes,
    message_routes,
    knowledge_routes,
    stats_routes,
    search_routes,
    ai_circle_routes,
    export_routes,
    market_routes,
    wisdom_space_routes,
    transfer_routes,
    user_routes,
    memory_routes,
    work_routes,
    pollination_routes,
    commander_routes,
    quality_routes,
    rescue_routes,
    pet_routes,
    base_routes,
    backup_routes,
    onboarding_routes,
    compute_routes,
    yunchong_routes,
    swarm_routes,
)


async def periodic_summary_task():
    while True:
        try:
            with db_cursor() as cur:
                cur.execute("SELECT id FROM users")
                user_ids = [row["id"] for row in cur.fetchall()]

            for uid in user_ids:
                try:
                    memory_service.summarize_work_logs(uid, hours=6)
                except Exception as e:
                    print(f"用户 {uid} 定期总结失败: {e}")
        except Exception as e:
            print(f"定期总结任务异常: {e}")

        await asyncio.sleep(6 * 3600)

async def periodic_git_push():
    """每小时把本地提交推送到 GitHub"""
    import subprocess
    import os as _os
    await asyncio.sleep(300)
    repo = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    while True:
        try:
            r = subprocess.run(
                "git push origin main",
                shell=True, cwd=repo, capture_output=True,
                encoding="utf-8", errors="replace", timeout=120
            )
            out = (r.stdout or "") + (r.stderr or "")
            if r.returncode == 0:
                if "Everything up-to-date" in out:
                    print("[git-push] 无新提交")
                else:
                    print(f"[git-push] 推送成功: {out.strip()[:200]}")
            else:
                print(f"[git-push] 推送失败: {out.strip()[:200]}")
        except Exception as e:
            print(f"[git-push] 异常: {e}")
        await asyncio.sleep(3600)



async def periodic_pattern_finalize():
    """每小时检查一次，把 24 小时前的 tentative pattern 转为 active"""
    while True:
        try:
            activated = pattern_service.finalize_patterns(hours=24)
            if activated:
                print(f"[pattern] finalize: {activated} 条转为 active")
        except Exception as e:
            print(f"[pattern] finalize 异常: {e}")
        await asyncio.sleep(3600)



async def periodic_rescue_maintenance():
    """每 5 分钟回收超时任务"""
    while True:
        try:
            reclaim_result = await asyncio.to_thread(rescue_service.reclaim_expired_tasks, 30)
            if reclaim_result.get("reclaimed", 0) > 0:
                print(f"[解救任务] 回收超时任务 {reclaim_result['reclaimed']} 个")
        except Exception as e:
            print(f"[解救任务] 维护异常: {e}")

        await asyncio.sleep(5 * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    try:
        backup_result = backup_service.create_backup()
        if backup_result["success"]:
            print(f"[备份] 启动备份成功: {backup_result['filename']}")
    except Exception as e:
        print(f"[备份] 启动备份异常: {e}")

    summary_task = asyncio.create_task(periodic_summary_task())
    debug_task = asyncio.create_task(debug_service.periodic_debug_scan(interval_hours=6, sample_limit=20))
    rescue_task = asyncio.create_task(periodic_rescue_maintenance())
    backup_task = asyncio.create_task(backup_service.periodic_backup_task())
    executor_task = asyncio.create_task(executor_service.start_background_executor())
    cleanup_task = asyncio.create_task(cleanup_service.periodic_cleanup(interval_hours=24))
    pattern_task = asyncio.create_task(periodic_pattern_finalize())
    git_push_task = asyncio.create_task(periodic_git_push())

    yield

    summary_task.cancel()
    debug_task.cancel()
    rescue_task.cancel()
    backup_task.cancel()
    executor_task.cancel()
    cleanup_task.cancel()
    pattern_task.cancel()


def create_app() -> FastAPI:
    app = FastAPI(title="SASES", version="0.15.4", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_routes.router)
    app.include_router(seed_routes.router)
    app.include_router(credit_routes.router)
    app.include_router(harness_routes.router)
    app.include_router(agi_routes.router)
    app.include_router(space_routes.router)
    app.include_router(group_routes.router)
    app.include_router(model_routes.router)
    app.include_router(agent_routes.router)
    app.include_router(chat_routes.router)
    app.include_router(message_routes.router)
    app.include_router(knowledge_routes.router)
    app.include_router(stats_routes.router)
    app.include_router(search_routes.router)
    app.include_router(ai_circle_routes.router)
    app.include_router(export_routes.router)
    app.include_router(market_routes.router)
    app.include_router(wisdom_space_routes.router)
    app.include_router(transfer_routes.router)
    app.include_router(user_routes.router)
    app.include_router(memory_routes.router)
    app.include_router(work_routes.router)
    app.include_router(pollination_routes.router)
    app.include_router(commander_routes.router)
    app.include_router(quality_routes.router)
    app.include_router(rescue_routes.router)
    app.include_router(pet_routes.router)
    app.include_router(base_routes.router)
    app.include_router(backup_routes.router)
    app.include_router(onboarding_routes.router)
    app.include_router(compute_routes.router)
    app.include_router(yunchong_routes.router)
    app.include_router(swarm_routes.router)

    @app.get("/static/index.html", response_class=HTMLResponse)
    async def serve_index():
        return FileResponse("static/index.html", media_type="text/html")

    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/")
    async def index():
        return FileResponse("static/index.html", media_type="text/html")

    @app.get("/favicon.ico")
    async def favicon():
        return FileResponse("static/favicon.svg", media_type="image/svg+xml")

    return app
