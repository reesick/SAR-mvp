import requests
import sys

API_BASE_URL = "http://localhost:8000"

def get_auth_token():
    try:
        data = {"username": "test@test.com", "password": "password123"}
        r = requests.post(f"{API_BASE_URL}/auth/login", data=data)
        if r.status_code == 200:
            return r.json()["access_token"]
        print("⚠️ Login failed, trying to register...")
        requests.post(f"{API_BASE_URL}/auth/register", json={"email": "test@test.com", "password": "password123"})
        r = requests.post(f"{API_BASE_URL}/auth/login", data=data) 
        return r.json()["access_token"]
    except Exception as e:
        print(f"❌ Auth Error: {e}")
        sys.exit(1)

def verify_export():
    print("🚀 STARTING SECTION 3 VERIFICATION")
    
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Create Case
    print("\n[1/3] Creating Case for Export Test...")
    r = requests.post(f"{API_BASE_URL}/cases/create", json={"customer_id": 1}, headers=headers)
    if r.status_code != 200:
        print(f"❌ Failed to create case: {r.text}")
        return
    case_id = r.json()["case_id"]
    print(f"✅ Case Created: {case_id}")

    # 2. Test Word Export
    print("\n[2/3] Testing Word Export...")
    sar_text = "This is a test SAR narrative for verification."
    export_data = {
        "sar_text": sar_text,
        "risk_score": 0.8,
        "recommendation": "FILE_SAR"
    }
    
    try:
        r = requests.post(
            f"{API_BASE_URL}/cases/{case_id}/export-docx-body",
            json=export_data,
            headers=headers
        )
        if r.status_code == 200:
            content_type = r.headers.get("Content-Type", "")
            if "wordprocessingml" in content_type:
                print(f"✅ Word Export Successful (Size: {len(r.content)} bytes)")
            else:
                print(f"⚠️ Word Export OK but weird Content-Type: {content_type}")
        else:
            print(f"❌ Word Export Failed: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"❌ Word Export Error: {e}")

    # 3. Test PDF Export
    print("\n[3/3] Testing PDF Export...")
    try:
        r = requests.post(
            f"{API_BASE_URL}/cases/{case_id}/export-pdf-body",
            json=export_data,
            headers=headers
        )
        if r.status_code == 200:
             content_type = r.headers.get("Content-Type", "")
             if "pdf" in content_type:
                print(f"✅ PDF Export Successful (Size: {len(r.content)} bytes)")
             else:
                print(f"⚠️ PDF Export OK but weird Content-Type: {content_type}")
        else:
            print(f"❌ PDF Export Failed: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"❌ PDF Export Error: {e}")

    print("\n🎉 SECTION 3 BACKEND VERIFICATION COMPLETE")

if __name__ == "__main__":
    verify_export()
