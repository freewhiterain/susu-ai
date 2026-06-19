"""
Langfuse 可观测性集成（加分项）。

设计原则：
- 完全可选：未配置 / 未安装 langfuse 时静默降级，不影响主流程。
- 零侵入：通过 observe_conversation() 上下文管理器包裹一次对话，
  记录输入、输出、模型、token、成本、延迟与工具调用。
"""
from contextlib import contextmanager
from typing import Any, Optional
from loguru import logger
from app.core.config import get_settings

_client: Any = None
_initialized = False


def _get_client() -> Optional[Any]:
    global _client, _initialized
    if _initialized:
        return _client
    _initialized = True

    s = get_settings()
    if not s.langfuse_enabled:
        logger.info("Langfuse 未启用（LANGFUSE_ENABLED=false）")
        return None
    if not (s.langfuse_secret_key and s.langfuse_public_key):
        logger.warning("Langfuse 已启用但缺少 key，跳过初始化")
        return None

    try:
        from langfuse import Langfuse
        _client = Langfuse(
            secret_key=s.langfuse_secret_key,
            public_key=s.langfuse_public_key,
            host=s.langfuse_host,
        )
        logger.info(f"Langfuse 已初始化：{s.langfuse_host}")
    except Exception as e:
        logger.warning(f"Langfuse 初始化失败，降级：{e}")
        _client = None
    return _client


class _Trace:
    """对 Langfuse trace 的轻量封装，无 client 时为 no-op。"""

    def __init__(self, trace: Any = None):
        self._trace = trace

    def update(self, **kwargs: Any) -> None:
        if self._trace is None:
            return
        try:
            self._trace.update(**kwargs)
        except Exception as e:
            logger.debug(f"Langfuse trace.update 失败：{e}")

    def score_reference(self, has_reference: bool) -> None:
        """记录本次回答是否带引用，作为质量信号。"""
        if self._trace is None:
            return
        try:
            self._trace.score(name="has_reference", value=1.0 if has_reference else 0.0)
        except Exception as e:
            logger.debug(f"Langfuse score 失败：{e}")


@contextmanager
def observe_conversation(
    *,
    session_id: str,
    platform: str,
    user_id: str,
    user_msg: str,
):
    """
    包裹一次完整对话。用法：

        with observe_conversation(...) as trace:
            ... 执行 agent ...
            trace.update(output=..., metadata={...})
            trace.score_reference(has_reference)
    """
    client = _get_client()
    trace_obj = None
    if client is not None:
        try:
            trace_obj = client.trace(
                name="xiaosu-chat",
                session_id=session_id,
                user_id=user_id or platform,
                input=user_msg,
                metadata={"platform": platform},
                tags=[platform],
            )
        except Exception as e:
            logger.debug(f"Langfuse trace 创建失败：{e}")

    trace = _Trace(trace_obj)
    try:
        yield trace
    finally:
        if client is not None:
            try:
                client.flush()
            except Exception:
                pass
