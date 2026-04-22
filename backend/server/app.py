from dotenv import load_dotenv
load_dotenv() # 加载环境变量，一定要放到最前方
from fastapi import FastAPI
from server.router import router
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from server.exception import register_exception
from server.middleware import register_middleware
from server.utils.db_helper import lark_monitor_db

# 服务启动或停止前后钩子，后续会用到
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 【启动阶段】
    lark_monitor_db.open() # 开启 Lark 库连接池
    print("🚀 PgSQL 连接池已就绪")

    # 如果有需要，可以在这里初始化表
    # await init_all_tables()

    yield  #【这里是应用运行阶段】

    # 【关闭阶段】
    #  彻底释放连接池
    await lark_monitor_db.close()
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
