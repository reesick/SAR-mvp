import requests
import time
import sys
import socket
from sqlalchemy import create_engine, text
from app.database import DATABASE_URL

API_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"

def check_frontend():
    print("\n🔍 CHECKING FRONTEND...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 3000))
    sock.close()
    if result == 0:
         print("✅ Frontend Port 3000: OPEN")
         return True
    else:
         print("❌ Frontend Port 3000: CLOSED")
         return False

def check_backend_health():
    print("\n🔍 CHECKING BACKEND API...")
    try:
        r = requests.get(f"{API_URL}/docs")
        if r.status_code == 200:
            print("✅ Backend API: ONLINE")
            return True
        else:
            print(f"❌ Backend API Error: {r.status_code}")
            return False
    except:
        print("❌ Backend API: OFFLINE")
        return False

def verify_analysis_fix():
    print("\n🚀 VERIFYING ANALYTICS FIX (Customer 7)...")
    try:
        # Login
        data = {"username": "test@test.com", "password": "password123"}
        r = requests.post(f"{API_URL}/auth/login", data=data)
        if r.status_code != 200:
            requests.post(f"{API_URL}/auth/register", json={"email": "test@test.com", "password": "password123"})
            r = requests.post(f"{API_URL}/auth/login", data=data) 
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create Case
        r = requests.post(f"{API_URL}/cases/create", json={"customer_id": 7}, headers=headers)
        case_id = r.json()["case_id"]
        
        # Run Analysis
        print("⏳ Analyzing...")
        r = requests.post(f"{API_URL}/cases/{case_id}/run-analysis?customer_id=7", headers=headers)
        result = r.json()
        
        risk = result.get("risk_score", 0.0)
        print(f"✅ Analysis Complete. Risk Score: {risk}")
        
        if risk > 0.3:
            print("✅ SUCCESS: High Risk Detected!")
            return True, case_id, headers
        else:
            print("❌ FAILURE: Risk Score too low.")
            return False, case_id, headers
            
    except Exception as e:
        print(f"❌ API Error: {e}")
        return False, None, None

def verify_export(case_id, headers):
    print("\n📄 VERIFYING DOCUMENT EXPORT...")
    if not case_id:
        print("❌ Skipping Export (No Case ID)")
        return

    # Word
    try:
        r = requests.post(f"{API_URL}/cases/{case_id}/export-docx-body", json={
            "sar_text": "TEST EXPORT", "risk_score": 0.9, "recommendation": "FILE SAR"
        }, headers=headers)
        if r.status_code == 200:
            print("✅ DOCX Export: SUCCESS")
        else:
            print(f"❌ DOCX Export Failed: {r.status_code}")
    except:
        print("❌ DOCX Export Error")

    # PDF
    try:
        r = requests.post(f"{API_URL}/cases/{case_id}/export-pdf-body", json={
            "sar_text": "TEST EXPORT", "risk_score": 0.9, "recommendation": "FILE SAR"
        }, headers=headers)
        if r.status_code == 200:
            print("✅ PDF Export: SUCCESS")
        else:
            print(f"❌ PDF Export Failed: {r.status_code}")
    except:
        print("❌ PDF Export Error")

if __name__ == "__main__":
    print("=== FINAL SYSTEM VERIFICATION ===")
    
    fe_ok = check_frontend()
    be_ok = check_backend_health()
    
    if be_ok:
        fix_ok, case_id, headers = verify_analysis_fix()
        if fix_ok:
            verify_export(case_id, headers)
    
    print("\n=== VERIFICATION COMPLETE ===")
