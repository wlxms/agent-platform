"""Billing service layer: in-memory usage records, cost calculation, summary aggregation."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone


def _calc_cost(input_tokens: int, output_tokens: int) -> float:
    return round(input_tokens * 0.00001 + output_tokens * 0.00003, 6)


SEED_RECORDS = [
    {
        "id": "rec-001",
        "time": "2026-04-15T10:30:00Z",
        "instance_name": "inst-001",
        "model": "gpt-4",
        "input_tokens": 1200,
        "output_tokens": 800,
    },
    {
        "id": "rec-002",
        "time": "2026-04-14T14:00:00Z",
        "instance_name": "inst-002",
        "model": "gpt-3.5-turbo",
        "input_tokens": 500,
        "output_tokens": 300,
    },
    {
        "id": "rec-003",
        "time": "2026-04-13T09:15:00Z",
        "instance_name": "inst-001",
        "model": "gpt-4",
        "input_tokens": 2000,
        "output_tokens": 1500,
    },
    {
        "id": "rec-004",
        "time": "2026-04-12T11:45:00Z",
        "instance_name": "inst-001",
        "model": "claude-3",
        "input_tokens": 800,
        "output_tokens": 600,
    },
    {
        "id": "rec-005",
        "time": "2026-04-11T16:20:00Z",
        "instance_name": "inst-002",
        "model": "gpt-3.5-turbo",
        "input_tokens": 300,
        "output_tokens": 200,
    },
]


class BillingService:
    def __init__(self, records: list[dict] | None = None):
        self._records = [self._enrich(r) for r in (records or [])]

    @staticmethod
    def _enrich(rec: dict) -> dict:
        return {
            **rec,
            "cost": _calc_cost(rec["input_tokens"], rec["output_tokens"]),
        }

    def get_summary(self, period: str = "month") -> dict:
        now = datetime.now(timezone.utc)
        if period == "month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start = now - timedelta(days=30)

        filtered = [
            r for r in self._records
            if datetime.fromisoformat(r["time"].replace("Z", "+00:00")) >= start
        ]

        total_tokens = sum(r["input_tokens"] + r["output_tokens"] for r in filtered)
        total_cost = round(sum(r["cost"] for r in filtered), 6)

        by_model_dict: dict[str, dict] = defaultdict(lambda: {"tokens": 0, "cost": 0.0})
        for r in filtered:
            key = r["model"]
            by_model_dict[key]["tokens"] += r["input_tokens"] + r["output_tokens"]
            by_model_dict[key]["cost"] = round(by_model_dict[key]["cost"] + r["cost"], 6)
        by_model = [{"model": m, "tokens": v["tokens"], "cost": v["cost"]} for m, v in by_model_dict.items()]

        daily_dict: dict[str, dict] = defaultdict(lambda: {"tokens": 0, "cost": 0.0})
        for r in filtered:
            day = r["time"][:10]
            daily_dict[day]["tokens"] += r["input_tokens"] + r["output_tokens"]
            daily_dict[day]["cost"] = round(daily_dict[day]["cost"] + r["cost"], 6)
        daily_trend = [{"date": d, "tokens": v["tokens"], "cost": v["cost"]} for d, v in sorted(daily_dict.items())]

        return {
            "total_tokens": total_tokens,
            "total_cost": total_cost,
            "by_model": by_model,
            "daily_trend": daily_trend,
        }

    def list_records(
        self,
        instance_id: str | None = None,
        model: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        filtered = list(self._records)

        if instance_id is not None:
            filtered = [r for r in filtered if r["instance_name"] == instance_id]
        if model is not None:
            filtered = [r for r in filtered if r["model"] == model]
        if start_date is not None:
            filtered = [r for r in filtered if r["time"][:10] >= start_date]
        if end_date is not None:
            filtered = [r for r in filtered if r["time"][:10] <= end_date]

        total = len(filtered)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_items = filtered[start_idx:end_idx]

        return {
            "items": page_items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }


_service: BillingService | None = None


def init_billing(records: list[dict] | None = None):
    global _service
    _service = BillingService(records or SEED_RECORDS)


def get_billing_service() -> BillingService:
    if _service is None:
        init_billing()
    return _service
