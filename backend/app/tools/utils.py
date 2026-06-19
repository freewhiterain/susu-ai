from datetime import datetime


def get_current_time() -> str:
    now = datetime.now()
    return (
        f"当前时间：{now.strftime('%Y年%m月%d日 %H:%M:%S')}，"
        f"星期{'一二三四五六日'[now.weekday()]}"
    )


async def dispatch(name: str, args: dict) -> str:
    """工具调度入口，根据名称路由到对应函数。"""
    from app.services.rag import get_rag

    if name == "search_docs":
        results = await get_rag().search(
            query=args.get("query", ""),
            n=args.get("n", 5),
        )
        if not results:
            return "知识库中未找到相关内容。"
        parts = []
        for r in results:
            parts.append(
                f"【来源：{r.filename}，第{r.chunk_index + 1}段，相关度{r.score:.2f}】\n{r.text}"
            )
        return "\n\n---\n\n".join(parts)

    if name == "get_employee":
        from app.tools.internal_api import get_employee
        return await get_employee(args.get("emp_id", ""))

    if name == "get_attendance":
        from app.tools.internal_api import get_attendance
        return await get_attendance(
            emp_id=args.get("emp_id", ""),
            start_date=args.get("start_date"),
            end_date=args.get("end_date"),
        )

    if name == "get_orders":
        from app.tools.internal_api import get_orders
        return await get_orders(
            start_date=args.get("start_date"),
            end_date=args.get("end_date"),
            status=args.get("status"),
        )

    if name == "get_current_time":
        return get_current_time()

    return f"未知工具：{name}"
