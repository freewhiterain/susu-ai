import json
import httpx
from loguru import logger
from app.core.config import get_settings


def _client() -> httpx.AsyncClient:
    s = get_settings()
    return httpx.AsyncClient(
        base_url=s.mock_api_base_url,
        timeout=s.mock_api_timeout,
    )


async def get_employee(emp_id: str) -> str:
    try:
        async with _client() as c:
            resp = await c.get(f"/api/employees/{emp_id}")
        if resp.status_code == 404:
            return f"未找到工号为 {emp_id} 的员工"
        resp.raise_for_status()
        data = resp.json()
        return json.dumps(data, ensure_ascii=False)
    except httpx.TimeoutException:
        logger.warning(f"get_employee timeout: emp_id={emp_id}")
        return "查询超时，请稍后重试"
    except Exception as e:
        logger.error(f"get_employee error: {e}")
        return f"查询失败：{e}"


async def get_attendance(
    emp_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    params: dict = {"emp_id": emp_id}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    try:
        async with _client() as c:
            resp = await c.get("/api/attendance", params=params)
        resp.raise_for_status()
        return json.dumps(resp.json(), ensure_ascii=False)
    except httpx.TimeoutException:
        logger.warning(f"get_attendance timeout: {params}")
        return "查询超时，请稍后重试"
    except Exception as e:
        logger.error(f"get_attendance error: {e}")
        return f"查询失败：{e}"


async def get_orders(
    start_date: str | None = None,
    end_date: str | None = None,
    status: str | None = None,
) -> str:
    params: dict = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if status:
        params["status"] = status
    try:
        async with _client() as c:
            resp = await c.get("/api/orders", params=params)
        resp.raise_for_status()
        return json.dumps(resp.json(), ensure_ascii=False)
    except httpx.TimeoutException:
        logger.warning(f"get_orders timeout: {params}")
        return "查询超时，请稍后重试"
    except Exception as e:
        logger.error(f"get_orders error: {e}")
        return f"查询失败：{e}"
