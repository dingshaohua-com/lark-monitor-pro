import os
import json
import asyncio
import lark_oapi as lark
from datetime import date
from lark_oapi.api.im.v1 import ListMessageRequest
from server.utils.date_helper import get_full_date_time

_client: lark.Client | None = None

def init_lark_client():
    global _client
    _client = (
        lark.Client.builder()
        .app_id(os.environ["LARK_APP_ID"])
        .app_secret(os.environ["LARK_APP_SECRET"])
        .log_level(lark.LogLevel.INFO)
        .build()
    )


def get_lark_client() -> lark.Client:
    if _client is None:
        raise RuntimeError("Lark client not initialized")
    return _client



async def fetch_msgs(client, container_type: str, container_id: str, start, end, callback, parent_node=None):
    """自动循环获取指定日期的所有数据（官方给的数据分页不是常规的totol、pagesize之类的，而是是否有下一页 page_token来决定是否有下页）"""
    print(container_type, container_id)
    page_token: str | None = None
    all_items: list[dict] = []
    page_num = 0
    while True:
        page_num += 1
        builder = (
            ListMessageRequest.builder()
            .container_id_type(container_type)
            .container_id(container_id)
            .page_size(50)
            .start_time(start)
            .end_time(end)
        )
        if page_token:
            builder = builder.page_token(page_token)

        response = await client.im.v1.message.alist(builder.build())
        if not response.success(): # ✅ 必须检查成功标志
            print(f"拉取失败! 错误码: {response.code}, 信息: {response.msg}")
            break
        items = response.data.items or []

        # 直接过滤 items 列表（排除回复还包含主消息的坑）
        if container_type == 'thread':
            items = [item for item in items if getattr(item, "parent_id", None)]

        is_last = not response.data.has_more

        # 给外部使用: 通知本次拉取完成
        _items = [json.loads(lark.JSON.marshal(item)) for item in items]

        if callback:
            result = callback(_items, parent_node=parent_node)
            if asyncio.iscoroutine(result):
                await result

        all_items.extend(_items)

        # 终止条件
        if is_last:
            break
        page_token = response.data.page_token

        # ✅ 防止限流：添加短暂延迟（可选），每10页暂停半秒
        if page_num % 10 == 0:
            await asyncio.sleep(0.5)
    return all_items


# 之前的版本是“全部主消息 -> 全部回复”，现在的版本是“主消息 P1 -> P1 回复 -> 主消息 P2...”
async def get_msgs(start: date | None = None, end: date | None = None, callback=None):
    client = get_lark_client()
    start, end = get_full_date_time(start, end, timestamp=True)
    chat_id = os.environ["MONITOR_CHAT_ID"]

    # 定义全量容器
    all_chat_items = []

    # 定义内部处理器：负责处理每一页主消息（与 fetch_msgs 的 callback(_items, parent_node=...) 对齐）
    async def main_msg_processor(items_dic, parent_node=None):
        # 1. 执行入库回调（分批入库，保证数据库安全）
        if callback:
            result = callback(items_dic, parent_node=parent_node)
            if asyncio.iscoroutine(result):
                await result

        # 2. 将这一页主消息塞进全量容器
        all_chat_items.extend(items_dic)

        # 3. 立即处理这页消息的回复
        for msg in items_dic:
            thread_id = msg.get("thread_id")
            if thread_id and thread_id != msg.get("message_id"):
                # 拉取回复：同样触发 callback 入库
                # 注意：这里我们把回复存入主消息对象的 'replies' 字段中
                replies = await fetch_msgs(
                    client, "thread", thread_id, start, end,
                    callback, parent_node=msg
                )
                msg['replies'] = replies

    # 启动同步：fetch_msgs 内部会不断调用 main_msg_processor
    await fetch_msgs(client, "chat", chat_id, start, end, main_msg_processor)

    # 最后大功告成，返回这个可能“撑爆”内存的巨无霸列表
    return all_chat_items