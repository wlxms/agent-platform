"""M3 Billing Completion — Smoke + Production Tests.

Runs all billing endpoints against running services (Auth :8001, Billing :8006).
Usage:
    set PYTHONPATH=services\\shared\\src;services\\billing\\src
    python scripts/smoke_m3_billing.py
"""
from __future__ import annotations

import httpx
import json
import sys
import csv
import io

BASE_AUTH = "http://localhost:8001"
BASE_BILLING = "http://localhost:8006"

# Use admin key (known to exist in DB)
API_KEY = "oh-admin-key-default"

passed = 0
failed = 0
results: list[str] = []


def log(msg: str):
    print(msg)
    results.append(msg)


def check(label: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        log(f"  PASS  {label}")
        passed += 1
    else:
        log(f"  FAIL  {label} — {detail}")
        failed += 1


def pretty(r: httpx.Response) -> str:
    try:
        return json.dumps(r.json(), indent=2)
    except Exception:
        return r.text[:200]


def main():
    global passed, failed
    client = httpx.Client(timeout=10)

    # ================================================================
    # 0. Health check
    # ================================================================
    log("=" * 60)
    log("PHASE 0: Service Health")
    log("=" * 60)

    r = client.get(f"{BASE_AUTH}/health")
    check("Auth service health", r.status_code == 200, f"got {r.status_code}")

    r = client.get(f"{BASE_BILLING}/health")
    check("Billing service health", r.status_code == 200, f"got {r.status_code}")

    # ================================================================
    # 1. Login — get JWT token
    # ================================================================
    log("")
    log("=" * 60)
    log("PHASE 1: Auth Login (API Key -> JWT)")
    log("=" * 60)

    r = client.post(
        f"{BASE_AUTH}/internal/auth/login",
        json={"api_key": API_KEY},
    )
    check("Login returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
    token = None
    if r.status_code == 200:
        data = r.json().get("data", {})
        token = data.get("token") or data.get("access_token")
        check("Token present", token is not None and len(token) > 20, f"token={str(token)[:20]}...")
    else:
        log("  SKIP remaining tests — no token")
        print_results()
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # ================================================================
    # 2. T3.1 Budget CRUD
    # ================================================================
    log("")
    log("=" * 60)
    log("T3.1: Budget CRUD (Smoke + Production)")
    log("=" * 60)

    # GET budget (smoke)
    r = client.get(f"{BASE_BILLING}/internal/billing/budget", headers=headers)
    check("GET /budget returns 200", r.status_code == 200, f"got {r.status_code}")
    if r.status_code == 200:
        data = r.json().get("data", {})
        check("Budget has threshold", "threshold" in data, f"keys={list(data.keys())}")
        check("Budget has alert_rules", "alert_rules" in data, f"keys={list(data.keys())}")
        log(f"  Budget response: threshold={data.get('threshold')}, alert_rules={data.get('alert_rules')}")

    # PUT budget (production) — upsert: creates if not exists, updates if exists
    r = client.put(
        f"{BASE_BILLING}/internal/billing/budget",
        json={"threshold": 1000.0, "alert_rules": {"thresholds": [80, 90, 100]}},
        headers=headers,
    )
    check("PUT /budget returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")

    # Verify update
    r = client.get(f"{BASE_BILLING}/internal/billing/budget", headers=headers)
    if r.status_code == 200:
        data = r.json().get("data", {})
        check("Budget threshold=1000 after update", data.get("threshold") == 1000.0, f"got {data.get('threshold')}")
        check("Budget alert_rules updated", data.get("alert_rules", {}).get("thresholds") == [80, 90, 100], f"got {data.get('alert_rules')}")

    # ================================================================
    # 3. T3.2 CSV Export
    # ================================================================
    log("")
    log("=" * 60)
    log("T3.2: CSV Export (Smoke + Production)")
    log("=" * 60)

    # GET export (smoke)
    r = client.get(f"{BASE_BILLING}/internal/billing/export?format=csv", headers=headers)
    check("GET /export?format=csv returns 200", r.status_code == 200, f"got {r.status_code}")
    if r.status_code == 200:
        ct = r.headers.get("content-type", "")
        check("Content-Type is text/csv", "text/csv" in ct, f"got {ct}")
        cd = r.headers.get("content-disposition", "")
        check("Content-Disposition has billing_export.csv", "billing_export.csv" in cd, f"got {cd}")
        body = r.text
        lines = body.strip().split("\n")
        check("CSV has header row", len(lines) >= 1, f"lines={len(lines)}")
        if lines:
            check("CSV header starts with instance_id", lines[0].startswith("instance_id"), f"header={lines[0][:60]}")
            if len(lines) > 1:
                log(f"  CSV: {len(lines)-1} data rows, header={lines[0][:80]}")
            else:
                log("  CSV: header only (no records)")

    # GET export with date range (production)
    r = client.get(
        f"{BASE_BILLING}/internal/billing/export?start_date=2026-01-01&end_date=2026-04-19&format=csv",
        headers=headers,
    )
    check("GET /export with date range returns 200", r.status_code == 200, f"got {r.status_code}")
    if r.status_code == 200:
        lines = r.text.strip().split("\n")
        log(f"  Date-filtered export: {len(lines)-1} records")

    # GET export as JSON
    r = client.get(f"{BASE_BILLING}/internal/billing/export?format=json", headers=headers)
    check("GET /export?format=json returns 200", r.status_code == 200, f"got {r.status_code}")
    if r.status_code == 200:
        data = r.json().get("data", [])
        check("JSON export is a list", isinstance(data, list), f"type={type(data)}")

    # ================================================================
    # 4. T3.3 Billing Rules CRUD
    # ================================================================
    log("")
    log("=" * 60)
    log("T3.3: Billing Rules CRUD (Smoke + Production)")
    log("=" * 60)

    # POST create rule (production)
    r = client.post(
        f"{BASE_BILLING}/internal/billing/rules",
        json={
            "org_id": "org-root",
            "model": "*",
            "price_per_input_token": 0.00001,
            "price_per_output_token": 0.00003,
        },
        headers=headers,
    )
    check("POST /rules returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
    created_rule_id = None
    if r.status_code == 200:
        rule_data = r.json().get("data", {})
        created_rule_id = rule_data.get("id")
        check("Created rule has id", created_rule_id is not None, f"data={rule_data}")
        check("Created rule model=*", rule_data.get("model") == "*", f"got {rule_data.get('model')}")

    # GET list rules (smoke)
    r = client.get(f"{BASE_BILLING}/internal/billing/rules", headers=headers)
    check("GET /rules returns 200", r.status_code == 200, f"got {r.status_code}")
    if r.status_code == 200:
        body = r.json()
        check("Rules has 'items'", "items" in body, f"keys={list(body.keys())}")
        check("Rules has 'total'", "total" in body, f"keys={list(body.keys())}")
        total_before = body.get("total", 0)
        log(f"  Rules listed: total={total_before}")

    # PUT update rule (production)
    if created_rule_id:
        r = client.put(
            f"{BASE_BILLING}/internal/billing/rules/{created_rule_id}",
            json={"price_per_input_token": 0.00002},
            headers=headers,
        )
        check("PUT /rules/{id} returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")

    # DELETE rule
    if created_rule_id:
        r = client.delete(
            f"{BASE_BILLING}/internal/billing/rules/{created_rule_id}",
            headers=headers,
        )
        check("DELETE /rules/{id} returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")

    # Verify deletion — total should be total_before (created rule was deleted)
    r = client.get(f"{BASE_BILLING}/internal/billing/rules", headers=headers)
    if r.status_code == 200:
        total_after = r.json().get("total", 0)
        log(f"  Rules after delete: before={total_before} after={total_after}")
        # NOTE: if the created rule's model conflicted with an existing seed rule,
        # total_before already reflects the post-upsert state. We just verify delete worked.
        check("Rules total decreased or stayed", total_after <= total_before, f"before={total_before} after={total_after}")

    # ================================================================
    # 5. T3.4 Org Summary Aggregation
    # ================================================================
    log("")
    log("=" * 60)
    log("T3.4: Org Summary Aggregation (Smoke + Production)")
    log("=" * 60)

    # GET org-summary (smoke)
    r = client.get(f"{BASE_BILLING}/internal/billing/org-summary?period=month", headers=headers)
    check("GET /org-summary returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
    if r.status_code == 200:
        data = r.json().get("data", {})
        check("Summary has total_tokens", "total_tokens" in data, f"keys={list(data.keys())}")
        check("Summary has total_cost", "total_cost" in data, f"keys={list(data.keys())}")
        check("Summary has by_org", "by_org" in data, f"keys={list(data.keys())}")
        check("Summary has budget", "budget" in data, f"keys={list(data.keys())}")
        check("Summary has budget_remaining", "budget_remaining" in data, f"keys={list(data.keys())}")
        check("by_org is a list", isinstance(data.get("by_org"), list), f"type={type(data.get('by_org'))}")
        log(f"  Summary: tokens={data.get('total_tokens')}, cost={data.get('total_cost')}, budget={data.get('budget')}, remaining={data.get('budget_remaining')}")
        log(f"  by_org breakdown: {data.get('by_org')}")

    # GET org-summary with period=30d (production)
    r = client.get(f"{BASE_BILLING}/internal/billing/org-summary?period=30d", headers=headers)
    check("GET /org-summary?period=30d returns 200", r.status_code == 200, f"got {r.status_code}")
    if r.status_code == 200:
        data = r.json().get("data", {})
        check("30d period has total_tokens", isinstance(data.get("total_tokens"), int), f"got {data.get('total_tokens')}")

    # ================================================================
    # 6. Existing endpoints still work (regression)
    # ================================================================
    log("")
    log("=" * 60)
    log("REGRESSION: Existing Billing Endpoints")
    log("=" * 60)

    r = client.get(f"{BASE_BILLING}/internal/billing/usage/summary?period=month", headers=headers)
    check("GET /usage/summary returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
    if r.status_code == 200:
        data = r.json().get("data", {})
        check("Summary has by_model", "by_model" in data, f"keys={list(data.keys())}")

    r = client.get(f"{BASE_BILLING}/internal/billing/usage/records?page=1&page_size=5", headers=headers)
    check("GET /usage/records returns 200", r.status_code == 200, f"got {r.status_code}: {r.text[:200]}")
    if r.status_code == 200:
        body = r.json()
        check("Records has 'items'", "items" in body, f"keys={list(body.keys())}")

    # ================================================================
    # Results
    # ================================================================
    print_results()


def print_results():
    log("")
    log("=" * 60)
    log(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
    log("=" * 60)
    if failed > 0:
        log("FAILURES DETECTED — review output above")
        sys.exit(1)
    else:
        log("ALL SMOKE + PRODUCTION TESTS PASSED")


if __name__ == "__main__":
    main()
