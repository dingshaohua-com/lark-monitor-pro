from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.middleware.response_wrapper import wrap_response


def register_middleware(server: FastAPI):
    # 解决跨域问题
    server.add_middleware(
        CORSMiddleware,  # type: ignore
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        max_age=600,
    )

    # 统一包装返回结构
    server.middleware("http")(wrap_response)