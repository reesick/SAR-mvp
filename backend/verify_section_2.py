import requests
import time
import sys
import json

API_BASE_URL = "http://localhost:8000"

def get_auth_token():
    """Get JWT token for testing"""
    try:
        data = {"username": "test@test.com", "password": "password123"}
        r = requests.post(f"{API_BASE_URL}/auth/login", data=data)
        if r.status_code == 200:
            return r.json()["access_token"]
        
        # If login fails, try registering first (in case DB was reset)
        print("⚠️ Login failed, trying to register...")
        requests.post(f"{API_BASE_URL}/auth/register", json={"email": "test@test.com", "password": "password123"})
        r = requests.post(f"{API_BASE_URL}/auth/login", data=data)
        return r.json()["access_token"]
    except Exception as e:
        print(f"❌ Auth Error: {e}")
        sys.exit(1)

def verify_section_2():
    print("🚀 STARTING SECTION 2 VERIFICATION")
    
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Verify Synthetic Data
    print("\n[1/4] Verifying Synthetic Data...")
    # We can't directly query DB via API easily without a specific endpoint, 
    # but running analysis will fail if no data.
    # We'll assume data is there from generate_data.py run.
    
    # 2. Create Case
    print("\n[2/4] Creating AML Case...")
    customer_id = 7 # We know Customer 7 has suspicious patterns from generate_data.py output
    
    try:
        r = requests.post(f"{API_BASE_URL}/cases/create", json={"customer_id": customer_id}, headers=headers)
        if r.status_code != 200:
            print(f"❌ Failed to create case: {r.text}")
            return
        
        case_data = r.json()
        case_id = case_data["case_id"]
        print(f"✅ Case Created: {case_id}")
    except Exception as e:
        print(f"❌ Case Creation Error: {e}")
        return

    # 3. Run Analysis (The Big One)
    print(f"\n[3/4] Running Full Analysis on Case {case_id}...")
    print("⏳ This triggers the LangGraph pipeline (Estimating 30-60s for LLM)...")
    
    start_time = time.time()
    try:
        r = requests.post(
            f"{API_BASE_URL}/cases/{case_id}/run-analysis", 
            params={"customer_id": customer_id}, 
            headers=headers,
            timeout=120 # Give it time for LLM
        )
        duration = time.time() - start_time
        
        if r.status_code != 200:
            print(f"❌ Analysis Failed: {r.status_code} - {r.text}")
            return
            
        result = r.json()
        print(f"✅ Analysis Complete ({duration:.1f}s)")
        print(f"   - Risk Score: {result['risk_score']}")
        print(f"   - Action: {result['recommended_action']}")
        print(f"   - Audit Log ID: {result['audit_log_id']}")
        print(f"   - SAR Draft Length: {len(result['sar_draft'])} chars")
        
        if result['risk_score'] > 0:
            print("✅ Risk Score indicates detection")
        else:
            print("⚠️ Risk Score is 0 (Unexpected for suspicious customer)")
            
    except Exception as e:
        print(f"❌ Analysis Error: {e}")
        return

    # 4. Verify Audit Trail
    print("\n[4/4] Verifying Audit Trail...")
    try:
        r = requests.get(f"{API_BASE_URL}/cases/{case_id}", headers=headers)
        if r.status_code != 200:
            print(f"❌ Failed to fetch audit logs: {r.text}")
            return
            
        logs = r.json()["audit_logs"]
        print(f"✅ Audit Logs Found: {len(logs)} entries")
        
        agents = set(l["agent_name"] for l in logs)
        print(f"   - Agents involved: {agents}")
        
        expected_agents = {"IngestionAgent", "AnalyticsAgent", "CorrelationAgent", "NarrativeAgent", "ComplianceAgent", "AuditLogger"}
        missing = expected_agents - agents
        
        if not missing:
            print("✅ All agents contributed to audit trail")
        else:
            print(f"⚠️ Missing agents in audit: {missing}")
            
    except Exception as e:
        print(f"❌ Audit Verification Error: {e}")
        return

    print("\n🎉 SECTION 2 VERIFICATION COMPLETE")

if __name__ == "__main__":
    verify_section_2()
