from fastapi import FastAPI
from server.exception.biz_error import BizError
from server.exception.error_handler import biz_error_handler, global_error_handler

def register_exception(server: FastAPI):
    # 注册自定义（业务）异常处理器
    server.add_exception_handler(BizError, biz_error_handler)
    # 注册全局异常处理器
    server.add_exception_handler(Exception, global_error_handler)