from app.services.llm.base import ToolDefinition

# Agent 工具调用最大轮次（防止无限循环），集中定义供 agent 与设置页共用
MAX_TOOL_ROUNDS_DEFAULT = 5

TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="search_docs",
        description=(
            "从公司知识库（员工手册、FAQ、规章制度等）中检索相关内容。"
            "当用户提问涉及公司政策、制度、流程时调用此工具。"
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "检索关键词或完整问题"},
                "n": {"type": "integer", "description": "返回结果数量，默认 5", "default": 5},
            },
            "required": ["query"],
        },
    ),
    ToolDefinition(
        name="get_employee",
        description="查询员工基本信息，包括姓名、部门、职级、入职日期等。",
        parameters={
            "type": "object",
            "properties": {
                "emp_id": {"type": "string", "description": "员工工号，如 '001'"},
            },
            "required": ["emp_id"],
        },
    ),
    ToolDefinition(
        name="get_attendance",
        description="查询员工考勤记录，包括打卡时间、迟到/早退/加班/请假状态。",
        parameters={
            "type": "object",
            "properties": {
                "emp_id": {"type": "string", "description": "员工工号"},
                "start_date": {"type": "string", "description": "起始日期 YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "截止日期 YYYY-MM-DD"},
            },
            "required": ["emp_id"],
        },
    ),
    ToolDefinition(
        name="get_orders",
        description="查询销售订单数据，支持按日期范围、状态筛选，并返回汇总金额。",
        parameters={
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "起始日期 YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "截止日期 YYYY-MM-DD"},
                "status": {
                    "type": "string",
                    "description": "订单状态：completed | pending | refunded",
                },
            },
            "required": [],
        },
    ),
    ToolDefinition(
        name="get_current_time",
        description="获取当前日期和时间，用于回答「现在几点」「今天是几号」等问题。",
        parameters={"type": "object", "properties": {}, "required": []},
    ),
]

TOOL_MAP: dict[str, ToolDefinition] = {t.name: t for t in TOOLS}
