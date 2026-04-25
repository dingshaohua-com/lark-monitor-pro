from fastapi import APIRouter
from . import root
from . import message
from . import bitable

# 创建父路由，统一添加 /api 前缀
router = APIRouter(prefix="/api")

@router.get("")
async def api_handler():
    return {"message": "i am root"}

# 将所有子路由注册到父路由
router.include_router(root.router)
router.include_router(message.router)
router.include_router(bitable.router)