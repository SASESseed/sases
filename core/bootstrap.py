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
from .services import supervisor_service
from .services import executor_service
from .services import cleanup_service
from .services import pattern_service
from .services import pattern_service
from . import backup_service
from .api_routes import (
    supervisor_routes,
    upload_routes,
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



async def periodic_syntax_check():
    """每 10 分钟检查 core/ 下 .py 语法，发现错误就告警"""
    import ast as _ast
    import os as _os
    await asyncio.sleep(60)
    while True:
        try:
            _bad = []
            for _root, _dirs, _files in _os.walk('core'):
                _dirs[:] = [d for d in _dirs if d not in ('__pycache__',)]
                for _f in _files:
                    if not _f.endswith('.py'):
                        continue
                    _fp = _os.path.join(_root, _f)
                    try:
                        with open(_fp, 'r', encoding='utf-8') as _fh:
                            _ast.parse(_fh.read())
                    except SyntaxError as _se:
                        _bad.append(_fp + ' (line ' + str(_se.lineno) + ')')
                    except Exception:
                        pass
            if _bad:
                print('[syntax-check] 发现语法错误: ' + ' | '.join(_bad))
                print('[syntax-check] 建议: 运行 git log 查看最近提交，必要时 git reset --hard HEAD~N 回滚')
        except Exception as _e:
            print('[syntax-check] 异常: ' + str(_e))
        await asyncio.sleep(600)



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
    asyncio.create_task(supervisor_service.resume_restart_pending_runs())
    init_db()

    # 启动时清理中断的 run 和任务（v0.18.0）
    try:
        from .db import db_cursor as _dbc
        with _dbc(commit=True) as _c:
            _c.execute("UPDATE supervisor_runs SET status='interrupted', finished_at=datetime('now') WHERE status='running'")
            _r1 = _c.rowcount
            _c.execute("UPDATE swarm_pending_tasks SET status='interrupted' WHERE status IN ('pending', 'running')")
            _r2 = _c.rowcount
        if _r1 or _r2:
            print(f"[bootstrap] 清理中断状态: runs={_r1}, tasks={_r2}")
    except Exception as _e:
        print(f"[bootstrap] 清理中断状态失败: {_e}")


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
    from .services import state_service as _state_svc
    _state_task = asyncio.create_task(_state_svc.periodic_state_sync(interval_hours=24))
    pattern_task = asyncio.create_task(periodic_pattern_finalize())
    git_push_task = asyncio.create_task(periodic_git_push())
    syntax_check_task = asyncio.create_task(periodic_syntax_check())


    async def _periodic_restart_watch():
        import os as _os_w
        _root = _os_w.path.dirname(_os_w.path.dirname(_os_w.path.abspath(__file__)))
        _fp = _os_w.path.join(_root, 'restart_signal.txt')
        await asyncio.sleep(5)
        while True:
            try:
                if _os_w.path.exists(_fp):
                    print('[bootstrap] restart_signal detected, exiting for wrapper to restart')
                    _os_w._exit(0)
            except Exception as _e_w:
                print('[bootstrap] restart watch err: ' + str(_e_w))
            await asyncio.sleep(3)

    _restart_watch_task = asyncio.create_task(_periodic_restart_watch())


    yield

    summary_task.cancel()
    debug_task.cancel()
    rescue_task.cancel()
    backup_task.cancel()
    executor_task.cancel()
    cleanup_task.cancel()
    _state_task.cancel()

    if '_restart_watch_task' in dir():
        _restart_watch_task.cancel()
    pattern_task.cancel()
    git_push_task.cancel()
    syntax_check_task.cancel()


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
    app.include_router(upload_routes.router)
    app.include_router(supervisor_routes.router)

    @app.get("/static/index.html", response_class=HTMLResponse)
    async def serve_index():
        return FileResponse("static/index.html", media_type="text/html")

    app.mount("/static", StaticFiles(directory="static"), name="static")
    import os as _os
    _os.makedirs('uploads', exist_ok=True)
    app.mount('/uploads', StaticFiles(directory='uploads'), name='uploads')
    import os as _os
    _os.makedirs('uploads', exist_ok=True)
    app.mount('/uploads', StaticFiles(directory='uploads'), name='uploads')

    @app.get("/")
    async def index():
        return FileResponse("static/index.html", media_type="text/html")

    @app.get("/favicon.ico")
    async def favicon():
        return FileResponse("static/favicon.svg", media_type="image/svg+xml")

    return app
