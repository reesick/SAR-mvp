from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Transaction, Account, Customer
from app.services.analytics import AnalyticsEngine
from app.database import DATABASE_URL
import pandas as pd

# Setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def debug_customer(customer_id):
    print(f"\n🔍 DEBUGGING CUSTOMER {customer_id}")
    
    # Check Accounts
    accounts = db.query(Account).filter(Account.customer_id == customer_id).all()
    print(f"Accounts Found: {len(accounts)}")
    
    for acc in accounts:
        print(f"\n  🏦 Account {acc.id} ({acc.account_type})")
        
        # Check Transactions
        txs = db.query(Transaction).filter(Transaction.account_id == acc.id).order_by(Transaction.timestamp).all()
        print(f"     Transactions: {len(txs)}")
        
        if len(txs) > 0:
            print("     Last 3 Txs:")
            for t in txs[-3:]:
                print(f"       - [{t.timestamp}] {t.transaction_type} ${t.amount}")
        
        # Run Analytics Engine MANUALLY
        engine_svc = AnalyticsEngine(db)
        
        print("     --- Running Analytics ---")
        try:
            results = engine_svc.detect_anomalies(acc.id)
            print(f"     Risk Score: {results['risk_score']}")
            print(f"     Structuring: {results['structuring_detected']}")
            print(f"     Z-Score Anomalies: {len(results['anomalies'])}")
            print(f"     Velocity Spike: {results['velocity_spike']}")
            
            # Deep Dive into Structuring if false
            if not results['structuring_detected']:
                print("     [DEBUG] Deep Dive Structuring Logic:")
                df = pd.DataFrame([{
                    "id": t.id,
                    "amount": float(t.amount),
                    "timestamp": t.timestamp,
                    "transaction_type": t.transaction_type
                } for t in txs])
                
                print(f"       -> Dtypes: \n{df.dtypes}")
                
                # Check amount stats
                print(f"       -> Amount Stats:\n{df['amount'].describe()}")
                
                # Print raw list of amounts > 9000
                high_amounts = [x for x in df['amount'] if x > 9000]
                print(f"       -> List > 9000: {high_amounts}")
                
                # Clean Data HERE too
                df["transaction_type"] = df["transaction_type"].str.strip().str.upper()
                
                unique_types = df['transaction_type'].unique()
                print(f"       -> Unique Types (Cleaned): {[f'|{x}|' for x in unique_types]}")
                
                # Check specifics of the 9805 transaction
                suspicious = df[df['amount'] > 9000]
                print(f"       -> Suspicious Rows (>9000):\n{suspicious[['timestamp', 'amount', 'transaction_type']]}")
                
                # Re-run logic step-by-step
                near_threshold = df[
                    (df["amount"] > 9000) & 
                    (df["amount"] < 10000) & 
                    (df["transaction_type"].isin(["DEPOSIT", "WITHDRAWAL"]))
                ]
                print(f"       -> Txs near 10k: {len(near_threshold)}")
                if len(near_threshold) > 0:
                    print(near_threshold)
                    
        except Exception as e:
            print(f"     ❌ ERROR: {e}")

if __name__ == "__main__":
    debug_customer(7)
