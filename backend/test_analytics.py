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

def test_customer_analytics(customer_id):
    print(f"\n🚀 TESTING ANALYTICS FOR CUSTOMER {customer_id}")
    
    # 1. Get Accounts
    accounts = db.query(Account).filter(Account.customer_id == customer_id).all()
    print(f"✅ Found {len(accounts)} Accounts")
    
    engine_svc = AnalyticsEngine(db)
    max_risk = 0.0
    
    for acc in accounts:
        print(f"\n  🏦 Analyzing Account {acc.id} ({acc.account_type})...")
        
        # Run Detection
        results = engine_svc.detect_anomalies(acc.id)
        
        print(f"     Risk Score: {results['risk_score']}")
        print(f"     Structuring: {results['structuring_detected']}")
        print(f"     Velocity Spike: {results['velocity_spike']}")
        print(f"     Z-Score Anomalies: {len(results['anomalies'])}")
        
        if results['risk_score'] > max_risk:
            max_risk = results['risk_score']
            
    print(f"\n📊 AGGREGATED RISK SCORE: {max_risk}")
    
    if max_risk > 0.3:
        print("✅ SUCCESS: High Risk Detected across accounts!")
    else:
        print("❌ FAILURE: Risk Score too low.")

if __name__ == "__main__":
    test_customer_analytics(10)
