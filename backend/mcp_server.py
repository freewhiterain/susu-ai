"""
小苏 MCP Server（加分项）

将小苏的内部能力（知识库检索、员工/考勤/订单查询、时间）以 MCP 协议暴露，
使任何兼容 MCP 的客户端（Claude Desktop、Cursor、自建 Agent 等）都能直接调用。

运行（stdio 传输）：
    uv run python -m mcp_server
或在 Claude Desktop 配置：
    {
      "mcpServers": {
        "xiaosu": {
          "command": "uv",
          "args": ["run", "python", "-m", "mcp_server"],
          "cwd": "/abs/path/to/backend"
        }
      }
    }

复用 app.tools.dispatch，与在线 Agent 走完全相同的工具实现，避免逻辑分叉。
"""
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from app.tools.registry import TOOLS
from app.tools.utils import dispatch

server = Server("xiaosu")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """把内部 ToolDefinition 映射为 MCP Tool。"""
    return [
        Tool(
            name=t.name,
            description=t.description,
            inputSchema=t.parameters,
        )
        for t in TOOLS
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """统一经由 dispatch 执行，返回纯文本结果。"""
    result = await dispatch(name, arguments or {})
    return [TextContent(type="text", text=result)]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
