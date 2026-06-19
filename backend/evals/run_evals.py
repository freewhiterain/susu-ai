"""
小苏离线评测脚本（加分项）

针对 evals/cases.json 中的用例，逐条调用真实 Agent（agent.run），
从四个维度打分：

  1. 工具选择正确率   — 是否调用了期望的工具
  2. 引用合规率       — 知识库类问题是否带【来源：】引用
  3. 关键词命中率     — 回答是否包含期望关键词
  4. 拒答正确率       — 越界问题是否如实拒答（不编造）

用法：
    uv run python -m evals.run_evals
    uv run python -m evals.run_evals --json report.json   # 额外输出 JSON 报告

注意：需要可用的 LLM API Key 与已索引的知识库（先跑 scripts/seed）。
"""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

# 允许以 `python -m evals.run_evals` 或直接执行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import agent  # noqa: E402
from app.services.session import new_session_id  # noqa: E402

CASES_FILE = Path(__file__).parent / "cases.json"

REFUSAL_HINTS = ["没找到", "没有找到", "未找到", "无法", "抱歉", "没有相关", "不清楚", "提供"]


def _tools_match(actual: list[str], expected: list[str]) -> bool:
    """期望的工具是否都被调用（允许额外调用）。"""
    if not expected:
        return True
    return all(e in actual for e in expected)


def _is_refusal(text: str) -> bool:
    return any(h in text for h in REFUSAL_HINTS)


async def run_case(case: dict) -> dict:
    t0 = time.monotonic()
    session_id = new_session_id()
    try:
        resp = await agent.run(
            user_msg=case["question"],
            session_id=session_id,
            platform="eval",
        )
        content = resp.content
        actual_tools = [tc.name for tc in resp.tool_calls]
        has_ref = len(resp.references) > 0 or "【来源：" in content
        error = None
    except Exception as e:
        content, actual_tools, has_ref, error = "", [], False, str(e)

    # ── 评分 ──
    checks = {}
    checks["tool"] = _tools_match(actual_tools, case.get("expect_tools", []))

    expect_kw = case.get("expect_keywords", [])
    checks["keywords"] = all(k in content for k in expect_kw) if expect_kw else True

    if case.get("expect_reference"):
        checks["reference"] = has_ref
    else:
        checks["reference"] = True  # 不要求引用则视为通过

    if case.get("expect_refusal"):
        checks["refusal"] = _is_refusal(content)
    else:
        checks["refusal"] = True

    passed = error is None and all(checks.values())

    return {
        "id": case["id"],
        "category": case["category"],
        "question": case["question"],
        "passed": passed,
        "checks": checks,
        "actual_tools": actual_tools,
        "has_reference": has_ref,
        "latency_ms": int((time.monotonic() - t0) * 1000),
        "error": error,
        "answer": content[:200],
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", help="输出 JSON 报告路径", default="")
    parser.add_argument("--filter", help="只跑某个 category 或 id 前缀", default="")
    args = parser.parse_args()

    data = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    cases = data["cases"]
    if args.filter:
        cases = [c for c in cases if args.filter in c["category"] or c["id"].startswith(args.filter)]

    print(f"\n{'='*70}")
    print(f"  小苏评测  |  共 {len(cases)} 个用例")
    print(f"{'='*70}\n")

    results = []
    for c in cases:
        r = await run_case(c)
        results.append(r)
        mark = "✅ PASS" if r["passed"] else "❌ FAIL"
        print(f"{mark}  [{r['category']}] {r['id']}")
        if not r["passed"]:
            failed_checks = [k for k, v in r["checks"].items() if not v]
            print(f"        未通过维度: {', '.join(failed_checks)}")
            if r["error"]:
                print(f"        错误: {r['error']}")
            print(f"        工具: {r['actual_tools']}  引用: {r['has_reference']}")
            print(f"        回答: {r['answer'][:80]}")

    # ── 汇总 ──
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    dims = ["tool", "keywords", "reference", "refusal"]
    dim_rates = {
        d: sum(1 for r in results if r["checks"][d]) / total if total else 0 for d in dims
    }
    avg_latency = sum(r["latency_ms"] for r in results) / total if total else 0

    print(f"\n{'='*70}")
    print(f"  总体通过率: {passed}/{total} = {passed/total*100:.1f}%")
    print(f"  工具选择正确率: {dim_rates['tool']*100:.1f}%")
    print(f"  关键词命中率:   {dim_rates['keywords']*100:.1f}%")
    print(f"  引用合规率:     {dim_rates['reference']*100:.1f}%")
    print(f"  拒答正确率:     {dim_rates['refusal']*100:.1f}%")
    print(f"  平均延迟:       {avg_latency:.0f} ms")
    print(f"{'='*70}\n")

    if args.json:
        report = {
            "summary": {
                "total": total,
                "passed": passed,
                "pass_rate": round(passed / total, 4) if total else 0,
                "dimension_rates": {k: round(v, 4) for k, v in dim_rates.items()},
                "avg_latency_ms": round(avg_latency, 1),
            },
            "results": results,
        }
        Path(args.json).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"JSON 报告已写入 {args.json}\n")

    # 通过率低于阈值时以非零码退出，便于 CI 拦截
    sys.exit(0 if total and passed / total >= 0.7 else 1)


if __name__ == "__main__":
    asyncio.run(main())
