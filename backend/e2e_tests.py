"""
End-to-end integration test suite for the Restaurant Management System.
Runs against a live backend at http://localhost:8000.

Uses timestamped unique values so it can be run repeatedly against the same DB.

Usage (inside the Docker backend container):
    python /app/e2e_tests.py
"""

import json
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timedelta, timezone

BASE = "http://localhost:8000"
PASS = "✅"
FAIL = "❌"
results = []

# Unique suffix so repeated runs don't collide
TS = str(int(time.time()))[-6:]
ADMIN_EMAIL = f"admin_{TS}@test.com"
STAFF_EMAIL = f"staff_{TS}@test.com"
TABLE_NUM1 = int(TS) % 900 + 100       # 100-999 range
TABLE_NUM2 = TABLE_NUM1 + 1


# ── HTTP helpers ───────────────────────────────────────────────────────────────

def req(method, path, body=None, token=None, form=False):
    url = BASE + path
    data = None
    headers = {}
    if body and not form:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    elif body and form:
        data = urllib.parse.urlencode(body).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            text = resp.read().decode()
            return resp.status, json.loads(text) if text.strip() else {}
    except urllib.error.HTTPError as e:
        text = e.read().decode()
        try:
            return e.code, json.loads(text)
        except Exception:
            return e.code, {"raw": text}


def check(name, status, body, expected_status=None, contains_key=None, value_check=None):
    ok = True
    reasons = []
    if expected_status and status != expected_status:
        ok = False
        reasons.append(f"status={status} want={expected_status}")
    if contains_key and contains_key not in body:
        ok = False
        reasons.append(f"missing key '{contains_key}'")
    if value_check and not value_check(body):
        ok = False
        reasons.append("value_check failed")
    icon = PASS if ok else FAIL
    msg = f"{icon}  {name}"
    if reasons:
        msg += f"  ← {'; '.join(reasons)}"
    if not ok:
        msg += f"\n     body={json.dumps(body)[:300]}"
    print(msg)
    sys.stdout.flush()
    results.append(ok)
    return ok, body


def section(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")
    sys.stdout.flush()


# ── wait for backend ───────────────────────────────────────────────────────────

def wait_for_backend(timeout=90):
    print(f"Waiting for backend at {BASE} ...")
    sys.stdout.flush()
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            status, body = req("GET", "/")
            if status == 200:
                print(f"  Backend ready ✓  ({body})\n")
                sys.stdout.flush()
                return True
        except Exception:
            pass
        time.sleep(2)
    print("  Backend did not start in time!")
    return False


if not wait_for_backend():
    sys.exit(1)

TOKEN = None
ADMIN_TOKEN = None
TABLE_ID = None
TABLE2_ID = None
MENU_ITEM_ID = None
MENU_ITEM2_ID = None


# ── 1. Health ─────────────────────────────────────────────────────────────────
section("1. Health Check")
check("GET /", *req("GET", "/"), expected_status=200, contains_key="status")


# ── 2. Auth ───────────────────────────────────────────────────────────────────
section("2. Auth — Register & Login")

ok, body = check(f"POST /auth/register (admin) [{ADMIN_EMAIL}]",
    *req("POST", "/auth/register", {"name": "Admin User", "email": ADMIN_EMAIL, "password": "secret123", "role": "admin"}),
    expected_status=201, contains_key="id")

ok, body = check(f"POST /auth/register (staff) [{STAFF_EMAIL}]",
    *req("POST", "/auth/register", {"name": "Staff User", "email": STAFF_EMAIL, "password": "secret123", "role": "staff"}),
    expected_status=201, contains_key="id")

ok, body = check("POST /auth/login (admin)",
    *req("POST", "/auth/login", {"username": ADMIN_EMAIL, "password": "secret123"}, form=True),
    expected_status=200, contains_key="access_token")
if ok:
    ADMIN_TOKEN = body["access_token"]

ok, body = check("POST /auth/login (staff)",
    *req("POST", "/auth/login", {"username": STAFF_EMAIL, "password": "secret123"}, form=True),
    expected_status=200, contains_key="access_token")
if ok:
    TOKEN = body["access_token"]

check("POST /auth/login (wrong password → 401)",
    *req("POST", "/auth/login", {"username": ADMIN_EMAIL, "password": "wrongpass"}, form=True),
    expected_status=401)

check("POST /auth/register (duplicate email → 400)",
    *req("POST", "/auth/register", {"name": "Dup", "email": ADMIN_EMAIL, "password": "x", "role": "staff"}),
    expected_status=400)


# ── 3. Tables ─────────────────────────────────────────────────────────────────
section("3. Tables CRUD")

check("GET /tables/ (public)",
    *req("GET", "/tables/"), expected_status=200,
    value_check=lambda b: isinstance(b, list))

ok, body = check(f"POST /tables/ T{TABLE_NUM1} (staff auth)",
    *req("POST", "/tables/", {"number": TABLE_NUM1, "capacity": 4, "status": "available"}, token=TOKEN),
    expected_status=201, contains_key="id")
if ok:
    TABLE_ID = body["id"]

ok, body = check(f"POST /tables/ T{TABLE_NUM2} (second table)",
    *req("POST", "/tables/", {"number": TABLE_NUM2, "capacity": 6, "status": "available"}, token=TOKEN),
    expected_status=201, contains_key="id")
if ok:
    TABLE2_ID = body["id"]

check("POST /tables/ (no auth → 401)",
    *req("POST", "/tables/", {"number": 9999, "capacity": 2, "status": "available"}),
    expected_status=401)

if TABLE_ID:
    check("GET /tables/{id}",
        *req("GET", f"/tables/{TABLE_ID}"), expected_status=200,
        value_check=lambda b: b.get("number") == TABLE_NUM1)

    check("PUT /tables/{id} (update status)",
        *req("PUT", f"/tables/{TABLE_ID}", {"status": "occupied"}, token=TOKEN),
        expected_status=200, value_check=lambda b: b.get("status") == "occupied")

    check("PUT /tables/{id} (revert to available)",
        *req("PUT", f"/tables/{TABLE_ID}", {"status": "available"}, token=TOKEN),
        expected_status=200)

    check("DELETE /tables/{id} (non-admin → 403)",
        *req("DELETE", f"/tables/{TABLE_ID}", token=TOKEN),
        expected_status=403)


# ── 4. Menu ───────────────────────────────────────────────────────────────────
section("4. Menu CRUD + Search")

ok, body = check("POST /menu/ (Beef Burger)",
    *req("POST", "/menu/", {"name": "Beef Burger", "category": "mains", "price": 12.99, "tags": "beef,grill"}, token=TOKEN),
    expected_status=201, contains_key="id")
if ok:
    MENU_ITEM_ID = body["id"]

ok, body = check("POST /menu/ (Cola)",
    *req("POST", "/menu/", {"name": "Cola", "category": "drinks", "price": 2.50, "tags": "cold"}, token=TOKEN),
    expected_status=201, contains_key="id")
if ok:
    MENU_ITEM2_ID = body["id"]

check("POST /menu/ (Brownie)",
    *req("POST", "/menu/", {"name": "Brownie", "category": "desserts", "price": 5.00, "tags": "sweet"}, token=TOKEN),
    expected_status=201)

check("GET /menu/",
    *req("GET", "/menu/"), expected_status=200,
    value_check=lambda b: len(b) >= 3)

check("GET /menu/search?q=be (Trie prefix → Beef Burger)",
    *req("GET", "/menu/search?q=be"), expected_status=200,
    value_check=lambda b: any("Beef" in i["name"] for i in b))

check("GET /menu/search?q=beef (Trie prefix)",
    *req("GET", "/menu/search?q=beef"), expected_status=200,
    value_check=lambda b: any("Burger" in i["name"] for i in b))

check("GET /menu/search?q=xyz (no results)",
    *req("GET", "/menu/search?q=xyz"), expected_status=200,
    value_check=lambda b: b == [])

check("GET /menu/category/drinks (hash map)",
    *req("GET", "/menu/category/drinks"), expected_status=200,
    value_check=lambda b: all(i["category"] == "drinks" for i in b) and len(b) >= 1)

check("GET /menu/category/nonexistent",
    *req("GET", "/menu/category/nonexistent"), expected_status=200,
    value_check=lambda b: b == [])

if MENU_ITEM_ID:
    check("GET /menu/{id}",
        *req("GET", f"/menu/{MENU_ITEM_ID}"), expected_status=200,
        value_check=lambda b: b.get("name") == "Beef Burger")

    check("DELETE /menu/{id} (non-admin → 403)",
        *req("DELETE", f"/menu/{MENU_ITEM_ID}", token=TOKEN),
        expected_status=403)

    check("DELETE /menu/{id} (admin → 204)",
        *req("DELETE", f"/menu/{MENU_ITEM_ID}", token=ADMIN_TOKEN),
        expected_status=204)


# ── 5. Waitlist ───────────────────────────────────────────────────────────────
section("5. Waitlist — Priority Queue")

check("POST /waitlist/join (VIP tier 1)",
    *req("POST", "/waitlist/join", {"guest_name": "Alice VIP", "party_size": 4, "priority_tier": 1}),
    expected_status=201, contains_key="position")

check("POST /waitlist/join (walk-in tier 3)",
    *req("POST", "/waitlist/join", {"guest_name": "Bob Walk-in", "party_size": 2, "priority_tier": 3}),
    expected_status=201, contains_key="position")

check("POST /waitlist/join (reservation tier 2)",
    *req("POST", "/waitlist/join", {"guest_name": "Carol Res", "party_size": 3, "priority_tier": 2}),
    expected_status=201, contains_key="position")

# GET /waitlist returns List[{position, score, entry:{...}}]
ok, body = check("GET /waitlist (sorted by priority score)",
    *req("GET", "/waitlist/"), expected_status=200,
    value_check=lambda b: len(b) >= 3 and "score" in b[0])
if ok:
    scores = [e["score"] for e in body]
    score_ok = scores == sorted(scores)
    icon = PASS if score_ok else FAIL
    print(f"  {icon}  Waitlist sorted ascending by score: {[round(s) for s in scores[:5]]}")
    sys.stdout.flush()
    results.append(score_ok)


# ── 6. Reservations ───────────────────────────────────────────────────────────
section("6. Reservations")

start_iso = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
ok, body = check("POST /reservations/",
    *req("POST", "/reservations/", {
        "guest_name": "Alice VIP",
        "party_size": 4,
        "start_time": start_iso,
        "duration_minutes": 60,
    }),
    expected_status=201, contains_key="id")

check("POST /reservations/ (second)",
    *req("POST", "/reservations/", {
        "guest_name": "Bob Walk-in",
        "party_size": 2,
        "start_time": (datetime.now(timezone.utc) + timedelta(hours=4)).isoformat(),
        "duration_minutes": 60,
    }),
    expected_status=201)

check("GET /reservations/",
    *req("GET", "/reservations/"), expected_status=200,
    value_check=lambda b: len(b) >= 2)


# ── 7. Table Allocation ────────────────────────────────────────────────────────
section("7. Table Allocation — Interval Scheduler")

check("GET /tables/allocate (greedy best-fit)",
    *req("GET", "/tables/allocate"), expected_status=200,
    value_check=lambda b: "assignments" in b and "unassigned_reservation_ids" in b)


# ── 8. Table Graph ────────────────────────────────────────────────────────────
section("8. Table Graph — BFS / Combine Tables")

if TABLE_ID and TABLE2_ID:
    check(f"POST /tables/{TABLE_ID}/adjacent/{TABLE2_ID} (add edge)",
        *req("POST", f"/tables/{TABLE_ID}/adjacent/{TABLE2_ID}", token=TOKEN),
        expected_status=201, contains_key="adjacent_table_ids")

    check("GET /tables/combine?party_size=8",
        *req("GET", "/tables/combine?party_size=8"), expected_status=200,
        value_check=lambda b: "viable_groups" in b)

    check("GET /tables/combine?party_size=100 (no group large enough)",
        *req("GET", "/tables/combine?party_size=100"), expected_status=200,
        value_check=lambda b: not any(g["can_seat_party"] for g in b.get("viable_groups", [])))

    check(f"DELETE /tables/{TABLE_ID}/adjacent/{TABLE2_ID} (remove edge)",
        *req("DELETE", f"/tables/{TABLE_ID}/adjacent/{TABLE2_ID}", token=TOKEN),
        expected_status=204)
else:
    print("  ⚠  Skipped (TABLE_ID not set — table creation failed above)")


# ── 9. Orders + Kitchen ───────────────────────────────────────────────────────
section("9. Orders — Queue Router + Kitchen View")

if MENU_ITEM2_ID and TABLE_ID and TOKEN:
    ok, body = check("POST /orders/ (staff auth, routes to station queues)",
        *req("POST", "/orders/", {
            "table_id": TABLE_ID,
            "menu_item_ids": [MENU_ITEM2_ID],
        }, token=TOKEN),
        expected_status=201, contains_key="routing")

    check("POST /orders/ (no auth → 401)",
        *req("POST", "/orders/", {"table_id": TABLE_ID, "menu_item_ids": [MENU_ITEM2_ID]}),
        expected_status=401)

    check("GET /kitchen/drinks",
        *req("GET", "/kitchen/drinks"), expected_status=200,
        value_check=lambda b: b["queue_length"] >= 1)

    check("GET /kitchen/grill",
        *req("GET", "/kitchen/grill"), expected_status=200,
        value_check=lambda b: "queue_length" in b and b["station"] == "grill")

    check("GET /kitchen/invalid (→ 404)",
        *req("GET", "/kitchen/invalid"), expected_status=404)
else:
    print("  ⚠  Skipped (menu item or table not available)")


# ── 10. Order History ─────────────────────────────────────────────────────────
section("10. Order History — BST Range Query")

today = datetime.utcnow().strftime("%Y-%m-%d")
yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
tomorrow = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")

check(f"GET /orders/history?from={yesterday}&to={tomorrow}",
    *req("GET", f"/orders/history?from={yesterday}&to={tomorrow}"),
    expected_status=200, value_check=lambda b: isinstance(b, list))

check("GET /orders/history (no filter — all orders)",
    *req("GET", "/orders/history"),
    expected_status=200, value_check=lambda b: isinstance(b, list))

check("GET /orders/history?from=2020-01-01&to=2020-01-02 (empty range)",
    *req("GET", "/orders/history?from=2020-01-01&to=2020-01-02"),
    expected_status=200, value_check=lambda b: b == [])


# ── 11. Staff (Admin only) ────────────────────────────────────────────────────
section("11. Staff — Admin-Only Routes")

check("GET /staff/ (staff token → 403)",
    *req("GET", "/staff/", token=TOKEN),
    expected_status=403)

check("GET /staff/ (admin token → 200)",
    *req("GET", "/staff/", token=ADMIN_TOKEN),
    expected_status=200, value_check=lambda b: len(b) >= 2)


# ── Summary ───────────────────────────────────────────────────────────────────
total = len(results)
passed = sum(results)
failed = total - passed

print(f"\n{'═'*60}")
print(f"  RESULTS:  {passed}/{total} passed   |   {failed} failed")
print(f"{'═'*60}")
sys.stdout.flush()

if failed:
    print(f"\n  Some tests failed — see ❌ lines above.\n")
    sys.exit(1)
else:
    print(f"\n  All integration tests passed! 🎉\n")
