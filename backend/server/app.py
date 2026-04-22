from fastapi import FastAPI
from dotenv import load_dotenv
from server.router import router
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from server.exception import register_exception
from server.middleware import register_middleware

# 加载环境变量
load_dotenv()

# 服务启动或停止前后钩子，后续会用到
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # todo: 服务启动时候执行
    yield
    # todo: 服务停止时候执行

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
