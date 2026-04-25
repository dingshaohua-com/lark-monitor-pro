"""值班表 / 问题原因表：从飞书多维表格同步到 PG，并提供查询"""
import logging
import re
from datetime import date

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import col, select

from server.model.duty_schedule import DutySchedule
from server.model.qa_tracking import QaTracking
from server.utils.db_helper import AsyncSession
from server.utils.lark_bitable_helper import list_bitable_records

logger = logging.getLogger(__name__)

DUTY_BITABLE_APP_TOKEN = "MkoQwxWq7i0fW9kEJk6cjDaKnCe"
DUTY_TABLE_ID = "tblwel6L7Yk9NUpU"

QA_TRACKING_APP_TOKEN = "QNstwKyaNihYv2kKcY4c2RZdn6d"
QA_TRACKING_TABLE_ID = "tblMSns5snZtf14F"

_FEEDBACK_ID_RE = re.compile(r"【反馈ID】[：:]\s*(\S+)")


# ─── 值班表 ──────────────────────────────────────────────


def _extract_duty_user_name(row: dict) -> str:
    for key in ("测试", "值班人", "值班人员", "负责人", "处理人"):
        value = (row or {}).get(key)
        if value:
            return str(value).strip()
    return ""


def _parse_duty_date(raw: str) -> date | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    if re.fullmatch(r"\d{13}", raw):
        try:
            return date.fromtimestamp(int(raw) / 1000)
        except Exception:
            return None
    try:
        return date.fromisoformat(raw[:10])
    except Exception:
        return None


async def get_duty_records(session: AsyncSession) -> dict:
    """从 PG 读取值班表，按日期倒序"""
    statement = select(DutySchedule).order_by(col(DutySchedule.duty_date).desc())
    result = await session.exec(statement)
    rows = list(result.all())
    records = [{"日期": r.duty_date.isoformat(), "值班人": r.duty_user} for r in rows]
    return {
        "total": len(records),
        "field_keys": ["日期", "值班人"],
        "records": records,
    }


async def sync_duty_to_pg(session: AsyncSession) -> int:
    """从飞书值班多维表格拉取数据，UPSERT 到 duty_schedule 表"""
    data = await list_bitable_records(DUTY_BITABLE_APP_TOKEN, DUTY_TABLE_ID)
    records: list[dict] = []
    for row in data.get("records", []):
        duty_date = _parse_duty_date(str(row.get("日期") or ""))
        duty_user = _extract_duty_user_name(row)
        if duty_date and duty_user:
            records.append({"duty_date": duty_date, "duty_user": duty_user})

    if records:
        stmt = pg_insert(DutySchedule).values(records)
        upsert = stmt.on_conflict_do_update(
            index_elements=["duty_date"],
            set_={"duty_user": stmt.excluded.duty_user},
        )
        await session.execute(upsert)
        await session.commit()

    logger.info("值班表已同步 %d 条", len(records))
    return len(records)


# ─── 问题原因表 ─────────────────────────────────────────


async def get_qa_tracking_records(session: AsyncSession) -> dict:
    """从 PG 读取 QA 跟进表"""
    statement = select(QaTracking)
    result = await session.exec(statement)
    rows = list(result.all())
    if not rows:
        return {"total": 0, "field_keys": [], "records": []}

    all_keys: dict[str, None] = {}
    records: list[dict] = []
    for r in rows:
        row = {"feedback_id": r.feedback_id, **(r.raw_data or {})}
        for k in row:
            all_keys.setdefault(k, None)
        records.append(row)
    field_keys = list(all_keys)
    return {"total": len(records), "field_keys": field_keys, "records": records}


async def sync_qa_tracking_to_pg(session: AsyncSession) -> int:
    """从飞书 QA 跟进多维表格拉取数据，UPSERT 到 qa_tracking 表"""
    data = await list_bitable_records(
        QA_TRACKING_APP_TOKEN, QA_TRACKING_TABLE_ID, max_records=5000
    )
    records: list[dict] = []
    for row in data.get("records", []):
        desc = row.get("反馈问题详细描述") or ""
        m = _FEEDBACK_ID_RE.search(desc)
        if m:
            records.append({"feedback_id": m.group(1), "raw_data": row})

    if records:
        stmt = pg_insert(QaTracking).values(records)
        upsert = stmt.on_conflict_do_update(
            index_elements=["feedback_id"],
            set_={"raw_data": stmt.excluded.raw_data},
        )
        await session.execute(upsert)
        await session.commit()

    logger.info("问题原因表已同步 %d 条", len(records))
    return len(records)
