from os import getenv
from typing import AsyncGenerator
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine

class DatabaseService:
    def __init__(self, uri: str, name: str):
        self.uri = uri
        self.name = name
        self.engine = None
        self.session_maker = None

    # 仪式感的核心：启动方法
    def open(self):
        self.engine = create_async_engine(
            self.uri,
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True
        )
        self.session_maker = sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        print(f"✨ [DB-{self.name}] 连接池已开启，准备就绪！")

    # 仪式感的核心：关闭方法
    async def close(self):
        if self.engine:
            await self.engine.dispose()
            print(f"🛑 [DB-{self.name}] 连接池已安全释放。")

    # 供 Depends 调用的生产器
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

# 预创建两个实例（此时只是配置，还没开工）
PGSQL_URI=getenv("PGSQL_URI")
print('PGSQL_URI'+PGSQL_URI)
lark_monitor_db_url=PGSQL_URI+"/lark_monitor"
lark_monitor_db = DatabaseService(lark_monitor_db_url, "lark_monitor")