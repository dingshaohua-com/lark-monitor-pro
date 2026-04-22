from functools import partial

async def get_all():
    return []



async def sync(start: date | None = None, end: date | None = None) :
    """从飞书群拉取原始消息（含话题回复）同步到表"""
    raw_col = get_collection("raw_msg")
    bound_callback = partial(sync_collection, raw_col)
    await get_msgs(start, end, bound_callback)
    return True