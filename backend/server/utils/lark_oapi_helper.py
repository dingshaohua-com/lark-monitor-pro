import os
import json
import asyncio
import lark_oapi as lark
from datetime import date
from server.utils.date_helper import get_full_date_time

ListMessageRequest = lark.api.im.v1
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



async def fetch_msgs(client, container_type: str, container_id: str, start, end, callback, parent_doc=None):
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
        items_dic = [json.loads(lark.JSON.marshal(item)) for item in items]

        if callback:
            result = callback(items_dic, items, is_last, parent_doc=parent_doc)
            if asyncio.iscoroutine(result):
                await result

        all_items.extend(items_dic)

        # 终止条件
        if is_last:
            break
        page_token = response.data.page_token

        # ✅ 防止限流：添加短暂延迟（可选），每10页暂停半秒
        if page_num % 10 == 0:
            await asyncio.sleep(0.5)
    return all_items



async def get_msgs(start: date | None = None, end: date | None = None, callback=None) :
    """从飞书群拉取原始消息（含话题回复）同步到表"""
    client = get_lark_client()
    start, end = get_full_date_time(start, end, timestamp=True)

    # 第一步：拉取群聊主消息（即话题）并入库
    chat_id = os.environ["MONITOR_CHAT_ID"]
    chat_items = await fetch_msgs(client,"chat", chat_id, start, end, callback)

    # 第二步：对有 thread_id 的消息，拉取话题内的回复
    for msg in chat_items:
        thread_id = msg.get("thread_id")
         # 跳过主消息（通过 ID 比对或层级判断）
        if thread_id == msg.get("message_id"):
            continue
        if thread_id:
            thread_items = await fetch_msgs(client,"thread", thread_id, start, end, callback, parent_doc=msg) # 表明这里是回复类型的消息，把主消息传进去，方便添加是否有机器人回复用
            msg['replies']=thread_items
    return chat_items