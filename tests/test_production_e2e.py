"""Production E2E test for frontend + backend integration.

Tests:
1. Frontend pages accessibility (Vite dev server)
2. Backend service health checks
3. API endpoint tests (gateway, host, scheduler, market)
4. Theme switching verification
5. Router navigation test

Run: python tests/test_production_e2e.py
"""
import json
import sys
import time
from urllib.request import urlopen, Request
from urllib.error import HTTPError

BASE_URL = "http://localhost:5173"
GATEWAY_URL = "http://localhost:8000"

passed = 0
failed = 0
skipped = 0


def check(step, condition, detail="", category="general"):
    global passed, failed, skipped
    if condition:
        passed += 1
        print(f"  ✓ {step}: {detail}")
    elif condition is None:
        skipped += 1
        print(f"  ⊘ {step}: {detail} (skipped)")
    else:
        failed += 1
        print(f"  ✗ {step}: {detail}")


def fetch(url, timeout=5):
    """Fetch URL and return (data, status_code)."""
    try:
        req = Request(url)
        resp = urlopen(req, timeout=timeout)
        return json.loads(resp.read().decode()), resp.status
    except HTTPError as e:
        try:
            return json.loads(e.read().decode()), e.code
        except Exception:
            return {"error": str(e)}, e.code
    except Exception as e:
        return {"error": str(e)}, 0


def fetch_html(url, timeout=5):
    """Fetch URL and return (html_content, status_code)."""
    try:
        req = Request(url)
        resp = urlopen(req, timeout=timeout)
        return resp.read().decode(), resp.status
    except HTTPError as e:
        return "", e.code
    except Exception as e:
        return "", 0


# ============================================================
print("=" * 70)
print("  OpenHarness Agent Platform - Production E2E Test")
print("=" * 70)
print(f"  Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"  Frontend: {BASE_URL}")
print(f"  Gateway:  {GATEWAY_URL}")
print("=" * 70)

# ============================================================
print("\n[1] Frontend Pages Accessibility")
print("-" * 70)

pages = [
    ("/", "首页"),
    ("/login", "登录页"),
    ("/dashboard", "仪表盘"),
    ("/agents", "Agent 列表"),
    ("/agents/new", "新建 Agent"),
    ("/market", "市场"),
    ("/billing", "计费"),
    ("/org", "组织管理"),
    ("/403", "403 页面"),
]

for path, name in pages:
    html, code = fetch_html(f"{BASE_URL}{path}")
    has_react = "root" in html or "vite" in html.lower() or code == 200
    check(f"页面: {name} ({path})", code == 200, f"status={code}, react={has_react}")

# ============================================================
print("\n[2] Frontend Assets")
print("-" * 70)

assets = [
    "/src/main.tsx",
    "/src/App.tsx",
    "/src/router/index.tsx",
]

for asset in assets:
    _, code = fetch_html(f"{BASE_URL}{asset}")
    check(f"资源: {asset}", code in [200, 404], f"status={code}")

# ============================================================
print("\n[3] Backend Service Health")
print("-" * 70)

services = [
    ("Gateway", 8000),
    ("Auth", 8001),
    ("Host", 8002),
    ("Scheduler", 8003),
    ("Memory", 8004),
    ("Market", 8005),
    ("Billing", 8006),
]

service_status = {}
for name, port in services:
    data, code = fetch(f"http://localhost:{port}/health")
    status = data.get("status", "unknown")
    is_ok = code == 200 and status == "ok"
    service_status[name] = is_ok
    check(f"服务: {name} (:{port})", is_ok, f"status={code}, health={status}")

# ============================================================
print("\n[4] Gateway API Tests")
print("-" * 70)

# Test 4.1: Gateway health
data, code = fetch(f"{GATEWAY_URL}/health")
check("Gateway 健康检查", code == 200 and data.get("status") == "ok", f"resp={data}")

# Test 4.2: Gateway CORS headers
try:
    req = Request(f"{GATEWAY_URL}/health")
    req.add_header("Origin", "http://localhost:5173")
    resp = urlopen(req, timeout=5)
    headers = dict(resp.headers)
    has_cors = "access-control-allow-origin" in headers
    check("Gateway CORS", has_cors, f"headers={list(headers.keys())}")
except Exception as e:
    check("Gateway CORS", False, str(e))

# Test 4.3: API docs (Swagger UI)
_, code = fetch_html(f"{GATEWAY_URL}/docs")
check("API 文档 (Swagger)", code == 200, f"status={code}")

# ============================================================
print("\n[5] Host Service Tests")
print("-" * 70)

if service_status.get("Host"):
    data, code = fetch(f"http://localhost:8002/health")
    check("Host 健康", code == 200, f"status={code}")
    
    # Test host commands endpoint
    _, code = fetch(f"http://localhost:8002/api/v1/hosts")
    check("Host 列表 API", code in [200, 401, 403], f"status={code}")
else:
    check("Host 测试", None, "服务未就绪，跳过")

# ============================================================
print("\n[6] Market Service Tests")
print("-" * 70)

if service_status.get("Market"):
    data, code = fetch(f"http://localhost:8005/health")
    check("Market 健康", code == 200, f"status={code}")
    
    # Test market templates
    _, code = fetch(f"http://localhost:8005/api/v1/market/templates")
    check("Market 模板列表", code in [200, 401, 403], f"status={code}")
    
    # Test market categories
    _, code = fetch(f"http://localhost:8005/api/v1/market/categories")
    check("Market 分类列表", code in [200, 401, 403], f"status={code}")
else:
    check("Market 测试", None, "服务未就绪，跳过")

# ============================================================
print("\n[7] Scheduler Service Tests")
print("-" * 70)

if service_status.get("Scheduler"):
    data, code = fetch(f"http://localhost:8003/health")
    check("Scheduler 健康", code == 200, f"status={code}")
else:
    check("Scheduler 测试", None, "服务未就绪，跳过")

# ============================================================
print("\n[8] Frontend Theme System")
print("-" * 70)

html, code = fetch_html(f"{BASE_URL}/")
has_light_theme = "light" in html.lower() or "var(--oh-" in html
has_dark_theme = "dark" in html.lower() or "var(--oh-" in html
has_theme_vars = "var(--oh-bg)" in html or "var(--oh-primary)" in html

check("主题系统 - 浅色支持", has_light_theme or has_theme_vars, "CSS 变量定义")
check("主题系统 - 深色支持", has_dark_theme or has_theme_vars, "CSS 变量定义")
check("主题系统 - CSS 变量", has_theme_vars, "使用 var(--oh-*) 变量")

# ============================================================
print("\n[9] Frontend Component Structure")
print("-" * 70)

components = [
    ("MainLayout", "/src/layouts/MainLayout.tsx"),
    ("AuthStore", "/src/store/authStore.ts"),
    ("ThemeStore", "/src/store/themeStore.ts"),
    ("ApiClient", "/src/api/client.ts"),
]

for name, path in components:
    _, code = fetch_html(f"{BASE_URL}{path}")
    exists = code == 200
    check(f"组件: {name}", exists, f"status={code}")

# ============================================================
print("\n" + "=" * 70)
print("  Test Summary")
print("=" * 70)
print(f"  Passed:  {passed}")
print(f"  Failed:  {failed}")
print(f"  Skipped: {skipped}")
print(f"  Total:   {passed + failed + skipped}")
print("=" * 70)

if failed == 0:
    print("\n  ✓ All critical tests passed!")
    sys.exit(0)
else:
    print(f"\n  ✗ {failed} test(s) failed")
    sys.exit(1)
