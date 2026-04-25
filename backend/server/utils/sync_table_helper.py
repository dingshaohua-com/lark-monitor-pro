import re
import json
from server.model.message import Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert


work_order_map = {
    "用户原文": "user_content",
    "功能异常": "func_exception",
    "优先级": "priority",
    "客户端": "client_type",
    "模块": "module",
    "内容标签": "content_tag",
    "反馈ID": "feedback_id",
    "一级标签": "tag_l1",
    "二级标签": "tag_l2",
    "三级标签": "tag_l3",
    "学段ID": "education_stage_id",
    "学科ID": "subject_id",
    "课程ID": "course_id",
    "课程版本": "course_version",
    "题集ID": "question_set_id",
    "题集版本": "question_set_version",
    "题目ID": "question_id",
    "题目版本": "question_version",
    "知识点ID": "knowledge_id",
    "词书ID": "wordbook_id",
    "单词组ID": "word_group_id",
    "单词ID": "word_id",
    "组件ID": "component_id",
    "组件版本": "component_version",
    "组件索引": "component_index",
    "版本号": "app_version",
    "设备型号": "device_model",
    "来源学校ID": "school_id",
    "来源学校名称": "school_name",
    "年级名称": "grade_name",
    "班级名称": "class_name",
    "学科名称": "subject_name",
    "姓名": "student_name",
    "uid": "uid",
    "线上反馈时间": "feedback_time",
    "创建时间":"create_time",
    "所属客服": "customer_service",
    "客服备注": "cs_remark",
    "文档ID": "doc_id",
    "播放时间线": "play_timeline",
    "扩展信息": "extra_info",
    "载荷链接": "payload_url",
    "查看线上版本": "online_version_url",
    "分类": "wo_type"
}

def convert_work_order_content(text: str) -> dict[str, str]:
    """将工单格式的文本解析为 {key: value, ...}。"""
    result = {}
    # 格式: 【标签】：值，每行一条
    pattern = re.compile(r"【([^】]+)】：(.*?)(?=\n【|$)", re.DOTALL)
    for label, value in pattern.findall(text):
        value = value.strip().rstrip("\n")
        key = work_order_map.get(label, label)
        result[key] = value
    return result


# 这样会跳过：
# 已撤回消息（"This message was recalled"）
# 合并转发消息（"Merged and Forwarded Message"）
# 其他无法解析为 JSON 的 content
def _parse_body_content(content):
    """安全解析 body.content：空串、非 JSON 字符串直接返回，避免 json.loads 报错"""
    if isinstance(content, (dict, list)):
        return content
    if not isinstance(content, str):
        return None
    content = content.strip()
    if not content:
        return None
    if content in ("This message was recalled", "Merged and Forwarded Message"):
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return content if content else None

# 跳过的飞书消息类型：飞书系统通知（入群/退群/改名等），与工单业务无关
SKIP_MSG_TYPES = {"system"}


async def sync_table_helper(session: AsyncSession, items,  parent_node ):
    if not items:
        return

    # 1. 准备批量数据列表（不直接 add，而是先准备数据）
    data_to_sync=[]
    for item in items:
        # 1.1 黑名单：飞书系统通知不入库
        if item.get("msg_type") in SKIP_MSG_TYPES:
            continue

        parse_body_content = _parse_body_content(item.get("body", {}).get("content"))
        # 1.2 撤回消息 / 合并转发 / 空 body：跳过（_parse_body_content 已返回 None）
        if parse_body_content is None:
            continue

        message = {
            "id": item.get("message_id"),
            "raw_data": item,
            "parsed_data": {
                "content": parse_body_content
            },
        }

        isRotSender = item.get("sender").get('sender_type') == "app" # 是否机器人发的消息

        if bool(item.get("parent_id")): # 如果是回复
            if isRotSender:
                message["type"] = "reply_by_robot"
            else:
                message["type"] = "reply_by_user"
        else: # 如果是主消息（工单）
            message["type"] = "thread"
            if isRotSender:  # 如果是机器人发送的
                raw_text = parse_body_content.get("elements")[0][0].get("text")
                parsedContent = convert_work_order_content(raw_text)
                message["parsed_data"]["content"] = parsedContent

        data_to_sync.append(message)

    if not data_to_sync:
        print(f"📦 [Sync] {len(items)} 条全部跳过（system / 撤回 / 空 body）")
        return

    # 2. 构造 PostgreSQL 特有的 UPSERT 语句
    # 这一步的仪式感在于：它保证了同步任务是“幂等”的（重复运行也不会报错）
    stmt = insert(Message).values(data_to_sync)

    upsert_stmt = stmt.on_conflict_do_update(
        index_elements=['id'],  # 冲突检测的字段
        set_={
            "raw_data": stmt.excluded.raw_data,  # 如果冲突，更新 raw_data 字段
        }
    )

    # 3. 一次性执行并提交
    await session.execute(upsert_stmt)
    await session.commit()

    skipped = len(items) - len(data_to_sync)
    print(f"📦 [Sync] 成功落盘 {len(data_to_sync)} 条" + (f"（跳过 {skipped} 条无效消息）" if skipped else ""))