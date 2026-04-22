"""Production-level end-to-end verification for M5-scheduler-orchestration.

Requires: All services running (auth:8001, host:8002, scheduler:8003, memory:8004, market:8005, billing:8006).
Run: cd agent-platform && ..\\.venv\\Scripts\\python.exe tests\\smoke_e2e_m5.py
"""
import asyncio
import json
import urllib.error
import urllib.request
import uuid

from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agentp_shared.config import db_settings
from agentp_shared.models import Base
from agentp_scheduler.lifecycle import create_task_record, get_task_status, update_task_status

SCHEDULER = "http://localhost:8003"
AUTH = "http://localhost:8001/internal/auth"

passed = 0
failed = 0


def req(method, path, base=SCHEDULER, token=None, body=None):
    url = f"{base}{path}"
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", f"Bearer {token}")
    try:
        resp = urllib.request.urlopen(r)
        return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read()), e.code
        except Exception:
            return {"error": e.reason}, e.code


def check(step, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {step} - {detail}")
    else:
        failed += 1
        print(f"  [FAIL] {step} - {detail}")


# ============================================================
print("=" * 60)
print("M5-SCHEDULER-ORCHESTRATION PRODUCTION END-TO-END")
print("=" * 60)

# ----------------------------------------------------------
print("\n[1] Health check aggregation (T5.1)")
# ----------------------------------------------------------
resp, code = req("GET", "/internal/health")
check("health status", code == 200, f"status={code}")
check("health has data", "data" in resp, "data key present")
if "data" in resp:
    data = resp["data"]
    check("health overall", data.get("overall") in ("ok", "degraded"), f"overall={data.get('overall')}")
    svc = data.get("services", {})
    check("health has services", len(svc) >= 5, f"{len(svc)} services")
    for name in ("auth", "host", "memory", "market", "billing"):
        check(f"health.{name}", name in svc and svc[name].get("status") in ("ok", "unavailable", "error"),
              f"{svc.get(name, {}).get('status', 'missing')}")

# ----------------------------------------------------------
print("\n[2] Login for auth token")
# ----------------------------------------------------------
resp, code = req("POST", "/login", base=AUTH, body={"api_key": "oh-admin-key-default"})
check("login", code == 200, f"status={code}")
login_data = resp.get("data", resp) if code == 200 else {}
token = login_data.get("token", "")
check("has token", bool(token), "token obtained")
org_id = login_data.get("org_id", "org-root")

# ----------------------------------------------------------
print("\n[3] Approval workflow - create (T5.2)")
# ----------------------------------------------------------
approval_suffix = uuid.uuid4().hex[:8]
create_body = {
    "org_id": org_id,
    "applicant_id": f"u-smoke-{approval_suffix}",
    "template_name": f"E2E-Test-{approval_suffix}",
    "config_summary": {"model": "gpt-4", "tone": "professional"},
    "reason": "M5 E2E smoke test",
}
resp, code = req("POST", "/internal/approvals", body=create_body)
check("create approval", code == 200, f"status={code}")
approval_id = resp.get("data", {}).get("id", "") if code == 200 else ""
check("has approval id", bool(approval_id), f"id={approval_id[:12]}...")
approval_status = resp.get("data", {}).get("status", "")
check("initial status pending", approval_status == "pending", f"status={approval_status}")

# ----------------------------------------------------------
print("\n[4] Approval workflow - list (T5.2)")
# ----------------------------------------------------------
resp, code = req("GET", f"/internal/approvals?org_id={org_id}&status=pending")
check("list approvals", code == 200, f"status={code}")
total = resp.get("total", 0)
check("list has items", total >= 1, f"total={total}")

# ----------------------------------------------------------
print("\n[5] Approval workflow - history (T5.2)")
# ----------------------------------------------------------
resp, code = req("GET", f"/internal/approvals/history?org_id={org_id}")
check("approval history", code == 200, f"status={code}")
history_total = resp.get("total", 0)
check("history has items", history_total >= 1, f"total={history_total}")

# ----------------------------------------------------------
print("\n[6] Approval workflow - approve (T5.2)")
# ----------------------------------------------------------
if approval_id:
    resp, code = req("POST", f"/internal/approvals/{approval_id}/approve",
                     body={"reviewer_id": "admin-e2e"})
    check("approve status", code == 200, f"status={code}")
    approve_data = resp.get("data", {})
    check("approve ok", approve_data.get("ok") is True, f"ok={approve_data.get('ok')}")
    check("approve status", approve_data.get("status") == "approved",
          f"status={approve_data.get('status')}")

    # Re-approve should fail (already approved)
    resp2, code2 = req("POST", f"/internal/approvals/{approval_id}/approve",
                       body={"reviewer_id": "admin-e2e"})
    check("re-approve rejected", code2 == 409, f"status={code2}")

# ----------------------------------------------------------
print("\n[7] Approval workflow - reject (T5.2)")
# ----------------------------------------------------------
reject_suffix = uuid.uuid4().hex[:8]
create2 = {
    "org_id": org_id,
    "applicant_id": f"u-smoke-{reject_suffix}",
    "template_name": f"Reject-Test-{reject_suffix}",
    "reason": "will be rejected",
}
resp, code = req("POST", "/internal/approvals", body=create2)
reject_id = resp.get("data", {}).get("id", "")
if reject_id:
    resp, code = req("POST", f"/internal/approvals/{reject_id}/reject",
                     body={"reviewer_id": "admin-e2e", "reason": "test rejection"})
    check("reject status", code == 200, f"status={code}")
    reject_data = resp.get("data", {})
    check("reject ok", reject_data.get("ok") is True)
    check("reject status", reject_data.get("status") == "rejected",
          f"status={reject_data.get('status')}")

# ----------------------------------------------------------
print("\n[8] Lifecycle management - via DB (T5.3)")
# ----------------------------------------------------------


async def test_lifecycle():
    engine = create_async_engine(db_settings.url, poolclass=NullPool)
    fac = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with fac() as s:
        # Create
        rec = await create_task_record(s, task_type="smoke_e2e", payload={"test": True})
        await s.commit()
        tid = rec["id"]
        check("create task", rec["status"] == "pending", f"id={tid[:12]}..., status={rec['status']}")

        # Get
        st = await get_task_status(s, task_id=tid)
        check("get task status", st is not None and st["status"] == "pending", f"status={st['status'] if st else 'None'}")

        # Update running
        await update_task_status(s, task_id=tid, status="running")
        await s.commit()
        st2 = await get_task_status(s, task_id=tid)
        check("update running", st2["status"] == "running", f"status={st2['status']}")
        check("started_at set", st2.get("started_at") is not None, f"started_at={st2.get('started_at')}")

        # Update completed
        await update_task_status(s, task_id=tid, status="completed", result={"success": True})
        await s.commit()
        st3 = await get_task_status(s, task_id=tid)
        check("update completed", st3["status"] == "completed", f"status={st3['status']}")
        check("completed_at set", st3.get("completed_at") is not None)
        check("result stored", st3.get("result") == {"success": True})

        # Not found
        missing = await get_task_status(s, task_id="nonexistent-id")
        check("nonexistent returns None", missing is None)

    await engine.dispose()


asyncio.run(test_lifecycle())

# ----------------------------------------------------------
print("\n[9] Lifecycle HTTP endpoint - 404 (T5.3)")
# ----------------------------------------------------------
resp, code = req("GET", "/internal/tasks/nonexistent-id")
check("task 404", code == 404, f"status={code}")
check("task 404 body", resp.get("code") == "NOT_FOUND", f"code={resp.get('code')}")

# ----------------------------------------------------------
print("\n[10] Celery task registration (T5.4)")
# ----------------------------------------------------------
try:
    from agentp_scheduler.celery_app import celery, process_approval_task
    check("celery app", celery is not None, "celery configured")
    check("celery main", celery.main == "agentp_scheduler", f"main={celery.main}")
    check("celery task", callable(process_approval_task), "process_approval_task callable")
except Exception as e:
    check("celery import", False, str(e))


# ============================================================
print("\n" + "=" * 60)
print(f"RESULTS: {passed}/{passed + failed} PASSED, {failed} FAILED")
if failed == 0:
    print("ALL M5 PRODUCTION TESTS PASSED!")
else:
    print("SOME TESTS FAILED - INVESTIGATE")
print("=" * 60)
