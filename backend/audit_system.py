import sys
import os
import requests
import socket
from sqlalchemy import create_engine, inspect, text
from app.database import DATABASE_URL
from app.models import Customer, Transaction, SARReport

def check_postgres():
    print("\n🔍 CHECKING DATABASE...")
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            print("✅ PostgreSQL Connection: OK")
            
            # Check Tables
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            print(f"✅ Found {len(tables)} Tables: {', '.join(tables)}")
            
            # Check Counts
            result = conn.execute(text("SELECT count(*) FROM customers")).scalar()
            print(f"📊 Customers: {result}")
            
            result = conn.execute(text("SELECT count(*) FROM transactions")).scalar()
            print(f"📊 Transactions: {result}")
            
            result = conn.execute(text("SELECT count(*) FROM sar_reports")).scalar()
            print(f"📊 SAR Reports: {result}")
            
            if result == 0:
                print("⚠️  Warning: No SAR Reports found. Analysis might not have run or failed.")
            else:
                print("✅ Data exists.")
                
    except Exception as e:
        print(f"❌ Database Error: {e}")
        print("   -> Is PostgreSQL running? Is the password correct in .env?")

def check_backend_env():
    print("\n🔍 CHECKING PYTHON ENVIRONMENT...")
    try:
        import pgvector
        print("✅ pgvector: Installed")
    except ImportError:
        print("❌ pgvector: MISSING (Did you activate venv?)")

    try:
        import langgraph
        print("✅ langgraph: Installed")
    except ImportError:
        print("❌ langgraph: MISSING")
        
    print(f"✅ Python Executable: {sys.executable}")

def check_ollama():
    print("\n🔍 CHECKING OLLAMA (AI)...")
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        if r.status_code == 200:
            models = [m['name'] for m in r.json()['models']]
            print(f"✅ Ollama Running. Models: {models}")
            if "mistral:7b-instruct-q4_K_M" in models:
                print("✅ Mistral 7B Model: Ready")
            else:
                print("⚠️  Mistral 7B Model: MISSING (Run 'ollama pull mistral:7b-instruct-q4_K_M')")
        else:
            print(f"❌ Ollama Error: Status {r.status_code}")
    except Exception as e:
        print(f"❌ Ollama Not Reachable: {e}")
        print("   -> Run 'ollama serve' in a separate terminal.")

def check_frontend():
    print("\n🔍 CHECKING FRONTEND...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 3000))
    if result == 0:
         print("✅ Frontend Port 3000: OPEN (UI is running)")
    else:
         print("❌ Frontend Port 3000: CLOSED (Run 'npm start' in frontend folder)")
    sock.close()

if __name__ == "__main__":
    print("=== SYSTEM AUDIT START ===")
    check_backend_env()
    check_postgres()
    check_ollama()
    check_frontend()
    print("\n=== AUDIT COMPLETE ===")
