"""Benchmark low-cost models on Workaholic's AI tasks before choosing a default.

Uses the configured AI provider (AI_PROVIDER + its settings) and treats each `--models`
entry as a deployment name. Deployments are expected to be named after their model
(e.g. deployment `gpt-5-nano` runs model gpt-5-nano) so costs can be estimated.

    uv run python -m benchmarks.run --models gpt-5-nano,gpt-5-mini --runs 3 --zone datazone

Results, including model outputs for the fictional inputs, are written to
benchmarks/results/ for human review.
"""

import argparse
import asyncio
import json
import statistics
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.core.errors import AppError
from app.services.ai.factory import build_llm_provider
from benchmarks.pricing import PriceZone, estimate_cost_usd
from benchmarks.tasks import ALL_TASKS

RESULTS_DIR = Path(__file__).parent / "results"


@dataclass
class CallRecord:
    model: str
    task: str
    run: int
    ok: bool
    error_code: str | None = None
    checks: dict[str, bool] = field(default_factory=dict)
    attempts: int = 0
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    cost_usd: float | None = None
    output: dict[str, Any] | None = None


async def benchmark(
    models: list[str], runs: int, zone: PriceZone, settings: Settings
) -> list[CallRecord]:
    provider = build_llm_provider(settings)
    if provider is None:
        raise SystemExit("AI_PROVIDER is disabled. Configure a provider before benchmarking.")

    records: list[CallRecord] = []
    try:
        for model in models:
            for task in ALL_TASKS:
                for run in range(1, runs + 1):
                    record = CallRecord(model=model, task=task.name, run=run, ok=False)
                    try:
                        result = await provider.structured_output(
                            task.messages,
                            task.schema,
                            operation=f"benchmark.{task.name}",
                            model=model,
                        )
                    except AppError as exc:
                        record.error_code = exc.code
                    else:
                        record.ok = True
                        record.checks = task.check(result.value)
                        record.attempts = result.attempts
                        record.latency_ms = result.latency_ms
                        record.input_tokens = result.usage.input_tokens
                        record.output_tokens = result.usage.output_tokens
                        record.reasoning_tokens = result.usage.reasoning_tokens
                        record.cost_usd = estimate_cost_usd(
                            model, zone, result.usage.input_tokens, result.usage.output_tokens
                        )
                        record.output = result.value.model_dump()
                    records.append(record)
                    status = "ok " if record.ok else f"ERR {record.error_code}"
                    failed = [name for name, passed in record.checks.items() if not passed]
                    print(f"  {model:16} {task.name:20} run {run}: {status} {failed or ''}")
    finally:
        await provider.aclose()
    return records


def summarise(records: list[CallRecord]) -> list[dict[str, Any]]:
    summary = []
    for model in dict.fromkeys(record.model for record in records):
        rows = [r for r in records if r.model == model]
        ok = [r for r in rows if r.ok]
        checks = [passed for r in ok for passed in r.checks.values()]
        latencies = sorted(r.latency_ms for r in ok)
        costs = [r.cost_usd for r in ok if r.cost_usd is not None]
        summary.append(
            {
                "model": model,
                "calls": len(rows),
                "schema_valid_rate": round(len(ok) / len(rows), 3) if rows else 0.0,
                "check_pass_rate": round(sum(checks) / len(checks), 3) if checks else 0.0,
                "fully_correct_rate": round(
                    sum(1 for r in ok if all(r.checks.values())) / len(rows), 3
                )
                if rows
                else 0.0,
                "latency_p50_ms": round(statistics.median(latencies)) if latencies else None,
                "latency_p95_ms": round(latencies[int(0.95 * (len(latencies) - 1))])
                if latencies
                else None,
                "avg_input_tokens": round(statistics.mean(r.input_tokens for r in ok))
                if ok
                else None,
                "avg_output_tokens": round(statistics.mean(r.output_tokens for r in ok))
                if ok
                else None,
                "avg_reasoning_tokens": round(statistics.mean(r.reasoning_tokens for r in ok))
                if ok
                else None,
                "cost_per_1000_calls_usd": round(statistics.mean(costs) * 1000, 3)
                if costs
                else None,
                "failed_checks": sorted(
                    {
                        f"{r.task}.{name}"
                        for r in ok
                        for name, passed in r.checks.items()
                        if not passed
                    }
                ),
            }
        )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--models", required=True, help="Comma-separated deployment names")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--zone", choices=["global", "datazone"], default="datazone")
    parser.add_argument("--max-output-tokens", type=int, default=2000)
    parser.add_argument("--reasoning-effort", choices=["none", "minimal", "low", "medium", "high"])
    args = parser.parse_args()

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    calls = len(models) * len(ALL_TASKS) * args.runs
    settings = Settings(
        ai_max_output_tokens=args.max_output_tokens,
        ai_reasoning_effort=args.reasoning_effort,
        log_level="WARNING",
    )
    print(f"Benchmarking {len(models)} model(s) x {len(ALL_TASKS)} tasks x {args.runs} runs")
    print(f"= {calls} calls, each capped at {args.max_output_tokens} output tokens")

    records = asyncio.run(benchmark(models, args.runs, args.zone, settings))
    summary = summarise(records)

    RESULTS_DIR.mkdir(exist_ok=True)
    path = RESULTS_DIR / f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
    path.write_text(
        json.dumps(
            {
                "provider": settings.ai_provider,
                "zone": args.zone,
                "runs": args.runs,
                "max_output_tokens": args.max_output_tokens,
                "reasoning_effort": args.reasoning_effort,
                "summary": summary,
                "records": [asdict(r) for r in records],
            },
            indent=2,
        )
    )
    print(json.dumps(summary, indent=2))
    total = sum(r.cost_usd or 0 for r in records)
    print(f"\nEstimated spend for this run: ${total:.4f}. Full results: {path}")
    if not any(r.ok for r in records):
        sys.exit(1)


if __name__ == "__main__":
    main()
