from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models import Base, Customer, Account, Transaction, AuditLog, SARReport
from app.database import DATABASE_URL
import pandas as pd

# Setup DB connection
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def print_table_summary(model, name):
    count = db.query(model).count()
    print(f"\n📊 {name}: {count} records")
    if count > 0:
        # Get first 3 records as example
        records = db.query(model).limit(3).all()
        for r in records:
            vars_dict = {k: v for k, v in vars(r).items() if not k.startswith('_')}
            print(f"  - {vars_dict}")

try:
    print("=== 🗄️ DATABASE CONTENT INSPECTION ===")
    
    # 1. Customers
    print_table_summary(Customer, "Customers")
    
    # 2. Accounts
    print_table_summary(Account, "Accounts")
    
    # 3. Transactions
    count_tx = db.query(Transaction).count()
    print(f"\n📊 Transactions: {count_tx} records")
    print("  (Showing last 3)")
    txs = db.query(Transaction).order_by(Transaction.timestamp.desc()).limit(3).all()
    for t in txs:
        print(f"  - ID: {t.id} | Amt: ${t.amount} | Type: {t.transaction_type} | Date: {t.timestamp}")

    # 4. Audit Logs (The Intelligence)
    count_logs = db.query(AuditLog).count()
    print(f"\n📊 Audit Logs: {count_logs} records")
    print("  (Showing last 5 actions)")
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(5).all()
    for l in logs:
        print(f"  - [{l.timestamp}] {l.agent_name}: {l.action_type}")

    # 5. Generated SARs
    # Note: SARReport model might not be populated if we just used agent state, 
    # but let's check if we saved them (we didn't explicitly save to SARReport table in main.py, 
    # only returned to frontend. But AgentReasoning has the drafts).
    
    # Check AgentReasoning for drafts
    from app.models import AgentReasoning
    reasonings = db.query(AgentReasoning).filter(AgentReasoning.agent_name == "NarrativeAgent").all()
    print(f"\n📊 Generated SAR Drafts (in Reasoning): {len(reasonings)}")
    for r in reasonings:
        print(f"  - Case {r.case_id}: {r.reasoning_json.get('draft_length', 'N/A')} chars")

except Exception as e:
    print(f"❌ Error: {e}")
finally:
    db.close()
