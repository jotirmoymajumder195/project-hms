#!/usr/bin/env python3
"""End-to-end MFA flow test"""
import json, time, hmac, hashlib, base64, struct, urllib.request, urllib.error

BASE = "http://localhost:5000/api/v1"
TENANT = "mbs"

def req(method, path, data=None, token=None):
    url = BASE + path
    body = json.dumps(data).encode() if data else None
    headers = {"Content-Type": "application/json", "x-tenant-id": TENANT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())

def totp(secret_b32):
    pad = (8 - len(secret_b32) % 8) % 8
    key = base64.b32decode(secret_b32.upper() + "=" * pad)
    counter = int(time.time()) // 30
    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    code = struct.unpack(">I", h[offset:offset+4])[0] & 0x7FFFFFFF
    return str(code % 1_000_000).zfill(6)

print("=" * 55)
print("HMS MFA End-to-End Test")
print("=" * 55)

# 1. Login — should return mfaSetupRequired
print("\n[1] Login with ADMIN-001...")
r = req("POST", "/auth/login", {"employeeId": "ADMIN-001", "password": "Admin@123!"})
assert r["success"], f"Login failed: {r}"
assert r.get("mfaSetupRequired") == True, f"Expected mfaSetupRequired, got: {r}"
token = r["token"]
print(f"    OK — success={r['success']} mfaSetupRequired={r.get('mfaSetupRequired')}")

# 2. Get MFA setup
print("\n[2] GET /auth/mfa/setup...")
r = req("GET", "/auth/mfa/setup", token=token)
assert r["success"], f"Setup failed: {r}"
secret = r["secret"]
assert len(secret) > 10
print(f"    OK — secret={secret[:10]}... qrCode={'yes' if r.get('qrCode') else 'no'}")

# 3. Confirm setup with valid TOTP
print("\n[3] POST /auth/mfa/setup/confirm...")
code = totp(secret)
print(f"    Using TOTP code: {code}")
r = req("POST", "/auth/mfa/setup/confirm", {"code": code}, token=token)
assert r["success"], f"Confirm failed: {r}"
print(f"    OK — {r['message']}")

# 4. Login again — should now return mfaRequired
print("\n[4] Login again (MFA now enabled)...")
r = req("POST", "/auth/login", {"employeeId": "ADMIN-001", "password": "Admin@123!"})
assert r["success"], f"Login2 failed: {r}"
assert r.get("mfaRequired") == True, f"Expected mfaRequired, got: {r}"
mfa_token = r["mfaToken"]
print(f"    OK — mfaRequired={r.get('mfaRequired')} mfaToken={mfa_token[:20]}...")

# 5. Complete MFA verify
print("\n[5] POST /auth/mfa/verify...")
time.sleep(1)
code = totp(secret)
print(f"    Using TOTP code: {code}")
r = req("POST", "/auth/mfa/verify", {"mfaToken": mfa_token, "code": code})
assert r["success"], f"MFA verify failed: {r}"
assert r.get("user", {}).get("role") == "ADMIN"
final_token = r["token"]
print(f"    OK — user={r['user']['name']} role={r['user']['role']}")

# 6. MFA status check
print("\n[6] GET /auth/mfa/status...")
r = req("GET", "/auth/mfa/status", token=final_token)
assert r["mfaEnabled"] == True
print(f"    OK — mfaEnabled={r['mfaEnabled']} mfaRequired={r['mfaRequired']}")

# 7. Disable MFA
print("\n[7] DELETE /auth/mfa (disable)...")
code = totp(secret)
r = req("DELETE", "/auth/mfa", {"code": code}, token=final_token)
assert r["success"], f"Disable failed: {r}"
print(f"    OK — {r['message']}")

# 8. Login again — should return mfaSetupRequired again
print("\n[8] Login after disable (should show mfaSetupRequired again)...")
r = req("POST", "/auth/login", {"employeeId": "ADMIN-001", "password": "Admin@123!"})
assert r.get("mfaSetupRequired") == True
print(f"    OK — mfaSetupRequired={r.get('mfaSetupRequired')}")

print("\n" + "=" * 55)
print("ALL TESTS PASSED")
print("=" * 55)
