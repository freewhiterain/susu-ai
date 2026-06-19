"""工具函数单元测试"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.tools.utils import get_current_time


def test_get_current_time_format():
    result = get_current_time()
    assert "年" in result and "月" in result and "日" in result
    assert "星期" in result


def test_get_current_time_is_string():
    assert isinstance(get_current_time(), str)


@pytest.mark.asyncio
async def test_get_employee_found():
    import json
    from app.tools.internal_api import get_employee

    mock_data = {"id": "001", "name": "张三", "dept": "研发部", "level": "P5"}
    with patch("app.tools.internal_api._client") as mock_ctx:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = lambda: None
        mock_ctx.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)

        result = await get_employee("001")

    data = json.loads(result)
    assert data["name"] == "张三"
    assert data["dept"] == "研发部"


@pytest.mark.asyncio
async def test_get_employee_not_found():
    from app.tools.internal_api import get_employee

    with patch("app.tools.internal_api._client") as mock_ctx:
        mock_resp = AsyncMock()
        mock_resp.status_code = 404
        mock_ctx.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)

        result = await get_employee("999")

    assert "未找到" in result


@pytest.mark.asyncio
async def test_get_attendance_with_date_range():
    from app.tools.internal_api import get_attendance

    mock_data = {"total_days": 5, "normal": 3, "late": 1, "absent": 1, "records": []}
    with patch("app.tools.internal_api._client") as mock_ctx:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = lambda: None
        mock_ctx.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)

        result = await get_attendance("001", "2026-06-09", "2026-06-13")

    import json
    data = json.loads(result)
    assert data["total_days"] == 5
    assert data["late"] == 1


@pytest.mark.asyncio
async def test_get_orders_sum():
    import json
    from app.tools.internal_api import get_orders

    mock_data = {
        "total_count": 3,
        "completed_count": 2,
        "total_amount": 18400.0,
        "orders": [],
    }
    with patch("app.tools.internal_api._client") as mock_ctx:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data
        mock_resp.raise_for_status = lambda: None
        mock_ctx.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)

        result = await get_orders(start_date="2026-06-01", end_date="2026-06-07")

    data = json.loads(result)
    assert data["total_amount"] == 18400.0


@pytest.mark.asyncio
async def test_get_employee_timeout():
    import httpx
    from app.tools.internal_api import get_employee

    with patch("app.tools.internal_api._client") as mock_ctx:
        mock_ctx.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.TimeoutException("timeout")
        )
        result = await get_employee("001")

    assert "超时" in result
