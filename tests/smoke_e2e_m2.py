"""Production-level end-to-end verification for M2-market-impl.

Requires: Market service running on :8005, Auth service running on :8001.
Run: cd agent-platform && .venv\\Scripts\\python.exe tests\\smoke_e2e_m2.py
"""
import json
import urllib.error
import urllib.request
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import asyncio

from agentp_shared.config import db_settings

BASE = "http://localhost:8005/internal/market"
AUTH_BASE = "http://localhost:8001/internal/auth"

passed = 0
failed = 0


def req(method, path, base=BASE, token=None, body=None):
    url = f"{base}{path}"
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", f"Bearer {token}")
    try:
        resp = urllib.request.urlopen(r)
        raw = resp.read()
        content_type = resp.headers.get("Content-Type", "")
        if "yaml" in content_type:
            return raw.decode("utf-8"), resp.status
        return json.loads(raw), resp.status
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


def check_not_empty(step, data, key):
    val = data.get(key) if isinstance(data, dict) else None
    check(step, val is not None and val != "" and val != [] and val != {},
          f"{key} present and non-empty")


# ============================================================
print("=" * 60)
print("M2-MARKET-IMPL PRODUCTION END-TO-END VERIFICATION")
print("=" * 60)

# Step 0: Get auth token
print("\n[0] Login to get auth token...")
resp, code = req("POST", "/login", base=AUTH_BASE, body={"api_key": "oh-admin-key-default"})
check("auth login", code == 200, f"status={code}")
if code != 200:
    print(f"  FATAL: Auth login failed. Start auth service on :8001. Response: {resp}")
    exit(1)
token = resp["data"]["token"]
check("auth token", token is not None, "token obtained")
org_id = resp["data"]["user"]["org_id"]
user_id = resp["data"]["user"]["id"]
print(f"  org_id={org_id}, user_id={user_id}")

tag = uuid.uuid4().hex[:8]

# Step 1: Health check
print("\n[1] GET /health...")
resp, code = req("GET", "/health", base="http://localhost:8005")
check("health status", code == 200, f"status={code}")

# Step 2: Template list (GET only — market has no POST /templates)
print("\n[2] Template list...")
resp, code = req("GET", "/templates", token=token)
check("list templates", code == 200, f"status={code}")
if code == 200:
    check("templates has items", "items" in resp, "items key present")
    check("templates has total", "total" in resp, "total key present")

resp, code = req("GET", "/templates/nonexistent-id", token=token)
check("template 404", code == 404, f"status={code}")

# Step 3: Skills
print("\n[3] Skills list...")
resp, code = req("GET", "/skills", token=token)
check("list skills", code == 200, f"status={code}")
if code == 200:
    check("skills has items", "items" in resp, "items key present")

# Step 4: MCP servers
print("\n[4] MCP servers list...")
resp, code = req("GET", "/mcps", token=token)
check("list mcps", code == 200, f"status={code}")

# Step 5: Categories
print("\n[5] Categories...")
resp, code = req("POST", "/categories", token=token, body={"name": f"smoke-cat-{tag}", "display_order": 99})
check("create category", code == 200, f"status={code}")
resp, code = req("GET", "/categories", token=token)
check("list categories", code == 200, f"status={code}")

# Step 6: Builder - Create Config
print("\n[6] Builder: AgentConfig CRUD...")
resp, code = req("POST", "/configs", token=token, body={
    "org_id": org_id, "author_id": user_id,
    "name": f"Builder Config {tag}",
    "model": {"provider": "litellm", "litellm_params": {"model": "openai/gpt-4o"}},
    "tools": ["Read", "Write"],
})
check("create config", code == 200, f"status={code}")
if code != 200:
    print(f"  FATAL: Cannot create config. Response: {resp}")
    config_id = None
else:
    config_id = resp["data"]["id"]
    check("config version", resp["data"].get("version") == "1.0.0", f"version={resp['data'].get('version')}")
    check_not_empty("config id", resp["data"], "id")

# Step 7: Get config
if config_id:
    print("\n[7] GET /configs/{id}...")
    resp, code = req("GET", f"/configs/{config_id}", token=token)
    check("get config", code == 200, f"status={code}")
    if code == 200 and isinstance(resp, dict) and "data" in resp:
        check("config name", resp["data"]["name"] == f"Builder Config {tag}")
    elif code != 200:
        check("get config detail", False, f"got status={code}")

# Step 8: List configs
if config_id:
    print("\n[8] GET /configs (list)...")
    resp, code = req("GET", f"/configs?org_id={org_id}", token=token)
    check("list configs", code == 200, f"status={code}")
    if code == 200:
        check("configs total >= 1", resp.get("total", 0) >= 1, f"total={resp.get('total')}")

# Step 9: Update config
if config_id:
    print("\n[9] PUT /configs/{id}...")
    resp, code = req("PUT", f"/configs/{config_id}", token=token, body={"name": f"Updated {tag}"})
    check("update config", code == 200, f"status={code}")
    if code == 200:
        check("updated version", resp["data"].get("version") == "1.0.1", f"version={resp['data'].get('version')}")

# Step 10: Get versions
if config_id:
    print("\n[10] GET /configs/{id}/versions...")
    resp, code = req("GET", f"/configs/{config_id}/versions", token=token)
    check("get versions", code == 200, f"status={code}")
    if code == 200:
        check("versions total >= 2", resp.get("total", 0) >= 2, f"total={resp.get('total')}")

# Step 11: Validate config
print("\n[11] POST /configs/validate...")
resp, code = req("POST", "/configs/validate", token=token, body={
    "personality": {"system_prompt": "You are a helpful assistant."},
    "model": {"provider": "litellm"},
    "permissions": {"mode": "default"},
})
check("validate valid", code == 200, f"status={code}")
if code == 200:
    check("validate result valid", resp["data"].get("valid") is True, f"valid={resp['data'].get('valid')}")

# Step 12: Validate invalid config
print("\n[12] POST /configs/validate (invalid)...")
resp, code = req("POST", "/configs/validate", token=token, body={
    "personality": {"system_prompt": ""},
    "permissions": {"mode": "superuser"},
})
check("validate invalid status", code == 200, f"status={code}")
if code == 200:
    check("validate invalid result", resp["data"].get("valid") is False, f"valid={resp['data'].get('valid')}")
    check("validate has errors", len(resp["data"].get("errors", [])) >= 2, f"errors={resp['data'].get('errors')}")

# Step 13: Export config (JSON)
if config_id:
    print("\n[13] GET /configs/{id}/export?format=json...")
    resp, code = req("GET", f"/configs/{config_id}/export?format=json", token=token)
    check("export json", code == 200, f"status={code}")
    # export returns raw JSON string, not wrapped in {"data": ...}
    if code == 200 and isinstance(resp, dict):
        check("export has name", "name" in resp, "name field present")
        check("export no internal id", "id" not in resp or resp.get("id") != config_id, "internal id stripped")

# Step 14: Export config (YAML)
if config_id:
    print("\n[14] GET /configs/{id}/export?format=yaml...")
    resp, code = req("GET", f"/configs/{config_id}/export?format=yaml", token=token)
    check("export yaml", code == 200, f"status={code}")
    if code == 200 and isinstance(resp, str):
        check("yaml has name", "name:" in resp, "contains 'name:' field")

# Step 15: Duplicate config
if config_id:
    print("\n[15] POST /configs/{id}/duplicate...")
    resp, code = req("POST", f"/configs/{config_id}/duplicate", token=token, body={"name": f"Clone {tag}"})
    check("duplicate config", code == 200, f"status={code}")
    if code == 200:
        dup_id = resp["data"]["id"]
        check("dup different id", dup_id != config_id, "new id differs from original")

# Step 16: Publish config
if config_id:
    print("\n[16] POST /configs/{id}/publish...")
    resp, code = req("POST", f"/configs/{config_id}/publish", token=token, body={
        "visibility": "org", "category": "published",
    })
    check("publish config", code == 200, f"status={code}")
    if code == 200:
        check("publish ok", resp["data"].get("ok") is True)
        check_not_empty("template_id", resp["data"], "template_id")

# Step 17: Import config (JSON)
print("\n[17] POST /configs/import...")
resp, code = req("POST", "/configs/import", token=token, body={
    "org_id": org_id, "author_id": user_id,
    "source": "json",
    "content": json.dumps({"name": f"Imported {tag}", "model": {"provider": "litellm"}}),
})
check("import config", code == 200, f"status={code}")

# Step 18: Import config (YAML)
print("\n[18] POST /configs/import (YAML)...")
resp, code = req("POST", "/configs/import", token=token, body={
    "org_id": org_id, "author_id": user_id,
    "source": "yaml",
    "content": f"name: ImportYaml{tag}\nmodel:\n  provider: litellm\n",
})
check("import yaml config", code == 200, f"status={code}")

# Step 19: Negative - Get nonexistent config
print("\n[19] Negative tests...")
resp, code = req("GET", "/configs/nonexistent-id", token=token)
check("get 404", code == 404, f"status={code}")

resp, code = req("GET", "/templates/nonexistent-id", token=token)
check("template 404", code == 404, f"status={code}")

# ============================================================
print("\n" + "=" * 60)
total = passed + failed
print(f"RESULTS: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print("ALL CHECKS PASSED!")
else:
    print(f"WARNING: {failed} checks failed")
print("=" * 60)

exit(0 if failed == 0 else 1)
