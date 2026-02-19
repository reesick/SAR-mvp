import requests
import time
import sys

API_URL = "http://localhost:8000"

def verify_customer_7():
    print("🚀 VERIFYING FIX FOR CUSTOMER 7")
    
    # 1. Login
    try:
        data = {"username": "test@test.com", "password": "password123"}
        r = requests.post(f"{API_URL}/auth/login", data=data)
        if r.status_code != 200:
            # Try Register
            requests.post(f"{API_URL}/auth/register", json={"email": "test@test.com", "password": "password123"})
            r = requests.post(f"{API_URL}/auth/login", data=data) 
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Logged In")
    except Exception as e:
        print(f"❌ Login Failed: {e}")
        return

    # 2. Create Case
    try:
        r = requests.post(f"{API_URL}/cases/create", json={"customer_id": 7}, headers=headers)
        if r.status_code != 200:
            print(f"❌ Create Case Failed: {r.text}")
            return
        case_id = r.json()["case_id"]
        print(f"✅ Case Created: {case_id}")
    except Exception as e:
        print(f"❌ Create Case Error: {e}")
        return

    # 3. Run Analysis
    print("⏳ Running Analysis (Wait 5s)...")
    try:
        start_time = time.time()
        r = requests.post(f"{API_URL}/cases/{case_id}/run-analysis?customer_id=7", headers=headers)
        if r.status_code != 200:
            print(f"❌ Analysis Failed: {r.text}")
            return
        result = r.json()
        duration = time.time() - start_time
        print(f"✅ Analysis Complete ({duration:.2f}s)")
        
        # 4. Check Results
        risk_score = result.get("risk_score", 0.0)
        rec = result.get("recommendation", "UNKNOWN")
        
        print(f"\n📊 RESULTS for Customer 7:")
        print(f"   Risk Score: {risk_score}")
        print(f"   Recommendation: {rec}")
        
        # Deep check logic
        if risk_score > 0.3:
            print("✅ SUCCESS: Risk Score detected!")
        else:
            print("❌ FAILURE: Risk Score still too low.")
            
        # Check logs if possible (via audit trail endpoint?)
        # For now, just trust the main result.
        
    except Exception as e:
        print(f"❌ API Call Error: {e}")

if __name__ == "__main__":
    verify_customer_7()
