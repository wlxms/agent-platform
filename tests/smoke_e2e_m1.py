"""Production-level end-to-end verification for M1-auth-rbac.

Run: cd agent-platform && .venv\\Scripts\\python.exe tests\\smoke_e2e_m1.py
"""
import asyncio
import json
import urllib.error
import urllib.request
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from agentp_auth import service
from agentp_shared import redis as shared_redis
from agentp_shared.config import db_settings
from agentp_shared.models import Organization, User

BASE = "http://localhost:8001/internal/auth"


def req(method, path, token=None, body=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", f"Bearer {token}")
    try:
        resp = urllib.request.urlopen(r)
        return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read()), e.code


engine = create_async_engine(db_settings.url, poolclass=NullPool)
factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
passed = 0
failed = 0


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
print("M1-AUTH-RBAC PRODUCTION END-TO-END VERIFICATION")
print("=" * 60)

# Step 1: Login
print("\n[1] Login with admin API key...")
resp, code = req("POST", "/login", body={"api_key": "oh-admin-key-default"})
check("login", code == 200, f"status={code}")
if code != 200:
    print(f"  FATAL: Cannot login, aborting. Response: {resp}")
    exit(1)
token = resp["data"]["token"]
user_role = resp["data"]["user"]["role"]
check("login role", user_role == "admin", f"role={user_role}")

# Step 2: Get permissions
print("\n[2] GET /permissions...")
resp, code = req("GET", "/permissions", token=token)
check("permissions status", code == 200, f"status={code}")
perm_count = resp["data"]["total"]
check("permissions count", perm_count == 14, f"got {perm_count}")
perm_ids = {p["id"] for p in resp["data"]["items"]}
check("permissions content", "agents:create" in perm_ids and "roles:manage" in perm_ids)

# Step 3: Get roles
print("\n[3] GET /roles...")
resp, code = req("GET", "/roles", token=token)
check("roles status", code == 200, f"status={code}")
role_count = resp["data"]["total"]
check("roles count", role_count == 3, f"got {role_count}")
role_map = {r["name"]: r["permissions"] for r in resp["data"]["items"]}
check("admin role", role_map.get("admin") == ["*"])
check("manager perms", len(role_map.get("manager", [])) == 7)
check("member perms", "agents:create" in role_map.get("member", []))

# Step 4: Setup test data
print("\n[4] Create test org + user for CRUD operations...")
tag = uuid.uuid4().hex[:8]


async def setup():
    shared_redis.redis_client = None
    async with factory() as db:
        await service.seed_default_data(db)
        org = Organization(name=f"Smoke Test Org {tag}")
        db.add(org)
        await db.commit()
        user = User(org_id=org.id, username=f"smoke-{tag}", email=f"smoke-{tag}@test.com", role="member", status="active")
        db.add(user)
        await db.commit()
        return org.id, user.id


org_id, user_id = asyncio.run(setup())
check("setup", org_id is not None and user_id is not None, f"org={org_id[:12]}... user={user_id[:12]}...")

# Step 5: POST - Add member (update role to manager)
print(f"\n[5] POST /org/{{id}}/members (add as manager)...")
resp, code = req("POST", f"/org/{org_id}/members", token=token, body={"user_id": user_id, "role": "manager"})
check("add member", code == 200, f"status={code}")
if code == 200:
    check("add member role", resp["data"]["role"] == "manager", f"role={resp['data']['role']}")
    check("add member org", resp["data"]["org_id"] == org_id)

# Step 6: PUT - Update role to admin
print(f"\n[6] PUT /org/{{id}}/members/{{uid}} (update to admin)...")
resp, code = req("PUT", f"/org/{org_id}/members/{user_id}", token=token, body={"role": "admin"})
check("update role", code == 200, f"status={code}")
if code == 200:
    check("update role value", resp["data"]["role"] == "admin", f"role={resp['data']['role']}")

# Step 7: DELETE - Remove member
print(f"\n[7] DELETE /org/{{id}}/members/{{uid}} (remove)...")
resp, code = req("DELETE", f"/org/{org_id}/members/{user_id}", token=token)
check("remove member", code == 200, f"status={code}")

# Step 8: Verify user status changed to "removed"
print("\n[8] Verify member status changed to 'removed'...")


async def verify_status():
    shared_redis.redis_client = None
    async with factory() as db:
        r = await db.execute(select(User).where(User.id == user_id))
        u = r.scalar_one_or_none()
        return u.status if u else "not_found"


status = asyncio.run(verify_status())
check("status removed", status == "removed", f"status={status}")

# Step 9: Create API key for renewal test
print("\n[9] Create API key for renewal test...")


async def create_key():
    shared_redis.redis_client = None
    async with factory() as db:
        await service.seed_default_data(db)
        return await service.create_api_key(db, org_id="org-root", user_id="user-admin", name="Smoke Renew Test", expires_in_days=5)


key_data = asyncio.run(create_key())
key_id = key_data["id"]
old_expires = key_data["expires_at"]
check("create key", key_id is not None, f"key={key_id[:12]}... expires={old_expires[:19]}")

# Step 10: Renew API key (30 days)
print("\n[10] POST /org/org-root/api-keys/{kid}/renew (30 days)...")
resp, code = req("POST", f"/org/org-root/api-keys/{key_id}/renew", token=token, body={"expires_in_days": 30})
check("renew key", code == 200, f"status={code}")
if code == 200:
    new_expires = resp["data"]["expires_at"]
    check("renew extended", new_expires > old_expires, f"{old_expires[:19]} -> {new_expires[:19]}")
    check("renew key_id", resp["data"]["key_id"] == key_id)

# Step 11: Negative test - invalid role
print("\n[11] Negative: POST members with invalid role...")
resp, code = req("POST", f"/org/{org_id}/members", token=token, body={"user_id": user_id, "role": "hacker"})
check("invalid role", code == 422, f"status={code} (expected 422)")

# Step 12: Negative test - remove nonexistent user
print("\n[12] Negative: DELETE nonexistent member...")
resp, code = req("DELETE", "/org/org-root/members/nonexistent-id", token=token)
check("remove nonexistent", code == 404, f"status={code} (expected 404)")

# Step 13: Negative test - renew nonexistent key
print("\n[13] Negative: RENEW nonexistent key...")
resp, code = req("POST", "/org/org-root/api-keys/nonexistent/renew", token=token, body={"expires_in_days": 30})
check("renew nonexistent", code == 404, f"status={code} (expected 404)")

# Step 14: Negative test - renew with invalid days
print("\n[14] Negative: RENEW with expires_in_days=-1...")
resp, code = req("POST", f"/org/org-root/api-keys/{key_id}/renew", token=token, body={"expires_in_days": -1})
check("renew invalid days", code == 422, f"status={code} (expected 422)")

# Step 15: Unauthorized access
print("\n[15] Negative: POST members without token...")
resp, code = req("POST", "/org/org-root/members", body={"user_id": "x", "role": "member"})
check("unauthorized", code == 401, f"status={code} (expected 401)")

# Cleanup
print("\n[16] Cleanup test data...")


async def cleanup():
    shared_redis.redis_client = None
    async with factory() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.execute(delete(Organization).where(Organization.id == org_id))
        await db.commit()


asyncio.run(cleanup())
check("cleanup", True, "test data cleaned up")

# Summary
print()
print("=" * 60)
total = passed + failed
print(f"RESULTS: {passed}/{total} PASSED, {failed} FAILED")
if failed == 0:
    print("ALL PRODUCTION TESTS PASSED")
else:
    print(f"FAILURES DETECTED: {failed}")
print("=" * 60)
exit(0 if failed == 0 else 1)
