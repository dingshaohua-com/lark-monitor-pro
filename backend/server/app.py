from dotenv import load_dotenv

from server.utils.lark_oapi_helper import init_lark_client

load_dotenv() # 加载环境变量，一定要放到最前方
from fastapi import FastAPI
from sqlmodel import SQLModel
from server.router import router
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from server.exception import register_exception
from server.middleware import register_middleware
from server.utils.db_helper import annotation_db, lark_monitor_db
from server.model.bot_reply import BotReply
from server.model.duty_schedule import DutySchedule
from server.model.qa_tracking import QaTracking
from server.scheduler import start_scheduler, stop_scheduler


async def _ensure_local_tables():
    """启动时确保本项目自有表存在（不影响其他外部表）"""
    async with lark_monitor_db.engine.begin() as conn:
        await conn.run_sync(
            SQLModel.metadata.create_all,
            tables=[
                BotReply.__table__,
                DutySchedule.__table__,
                QaTracking.__table__,
            ],
        )


# 服务启动或停止前后钩子，后续会用到
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 【启动阶段】
    init_lark_client()
    lark_monitor_db.open() # 开启 Lark 库连接池
    annotation_db.open() # 开启 annotation_db 连接池（仅用于 bot_reply 同步源端读取）
    print("🚀 PgSQL 连接池已就绪")

    await _ensure_local_tables()
    print("🗂️  本项目自有表已就绪 (bot_reply / duty_schedule / qa_tracking)")

    start_scheduler()
    print("⏰ 定时同步调度器已启动 (每日 00:01 UTC+8)")

    yield  #【这里是应用运行阶段】

    # 【关闭阶段】
    stop_scheduler()
    #  彻底释放连接池
    await lark_monitor_db.close()
    await annotation_db.close()
    print("🛑 PgSQL 连接池已安全关闭")

# 创建FastAPI实例（）
server = FastAPI(lifespan=lifespan)

# 注册中间件
register_middleware(server)

# 注册异常处理器
register_exception(server)

# 注册路由
server.include_router(router)

# 挂载静态资源
server.mount("/", StaticFiles(directory="server/static", html=True), name="static")
