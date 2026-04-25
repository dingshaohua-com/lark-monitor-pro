"""飞书多维表格通用读取工具：自动分页 + 字段值归一化"""
import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


async def get_tenant_access_token() -> str | None:
    """通过 LARK_APP_ID / LARK_APP_SECRET 获取 tenant_access_token"""
    app_id = os.environ.get("LARK_APP_ID", "")
    app_secret = os.environ.get("LARK_APP_SECRET", "")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(
                "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                json={"app_id": app_id, "app_secret": app_secret},
            )
            data = res.json()
            if data.get("code") == 0:
                return data.get("tenant_access_token")
            logger.error("获取 access_token 失败: %s", data)
    except Exception:
        logger.exception("获取 access_token 异常")
    return None


def _cell_to_str(value: Any) -> str:
    """把多维表格各种字段值统一成字符串"""
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return "、".join(_cell_to_str(x) for x in value if x is not None)
    if isinstance(value, dict):
        if "text" in value:
            return str(value.get("text") or "")
        if "name" in value:
            return str(value.get("name") or "")
        return json.dumps(value, ensure_ascii=False)
    return str(value)


async def list_bitable_records(
    app_token: str,
    table_id: str,
    max_records: int = 500,
) -> dict:
    """通用：拉取任意飞书多维表格的记录，自动分页 + 字段归一化"""
    access = await get_tenant_access_token()
    if not access:
        raise RuntimeError("无法获取飞书访问令牌，请检查 LARK_APP_ID / LARK_APP_SECRET")

    base = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
    headers = {
        "Authorization": f"Bearer {access}",
        "Content-Type": "application/json; charset=utf-8",
    }

    rows: list[dict[str, str]] = []
    page_token: str | None = None

    async with httpx.AsyncClient(timeout=20) as client:
        while len(rows) < max_records:
            params: dict[str, str | int] = {"page_size": min(100, max_records - len(rows))}
            if page_token:
                params["page_token"] = page_token
            res = await client.get(base, headers=headers, params=params)
            try:
                body = res.json()
            except Exception:
                logger.exception("多维表格响应非 JSON: status=%s", res.status_code)
                raise RuntimeError(f"飞书接口返回异常 HTTP {res.status_code}") from None
            if body.get("code") != 0:
                msg = body.get("msg", str(body))
                code = body.get("code")
                logger.warning("拉取多维表格失败: code=%s msg=%s", code, msg)
                raise RuntimeError(f"飞书多维表格错误 code={code}: {msg}")
            data = body.get("data") or {}
            for it in data.get("items") or []:
                rid = it.get("record_id", "")
                fields = it.get("fields") or {}
                row: dict[str, str] = {"record_id": rid}
                for k, v in fields.items():
                    row[k] = _cell_to_str(v)
                rows.append(row)
            if not data.get("has_more"):
                break
            page_token = data.get("page_token")
            if not page_token:
                break

    keys: list[str] = []
    for row in rows:
        for k in row:
            if k != "record_id" and k not in keys:
                keys.append(k)

    return {
        "total": len(rows),
        "field_keys": ["record_id", *keys],
        "records": rows,
    }
