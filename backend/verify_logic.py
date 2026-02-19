from app.database import SessionLocal
from app.services.analytics import AnalyticsEngine
from app.services.graph_analysis import GraphAnalyzer
from app.models import Customer, Account
import sys

def verify_analytics():
    print("\n--- Testing Analytics Engine ---")
    db = SessionLocal()
    try:
        # Find accounts with many transactions
        accounts = db.query(Account).all()
        for acc in accounts:
            engine = AnalyticsEngine(db)
            results = engine.detect_anomalies(acc.id)
            
            anomalies = len(results["anomalies"])
            structuring = results["structuring_detected"]
            velocity = results["velocity_spike"]
            risk = results["risk_score"]
            
            if anomalies > 0 or structuring or velocity:
                print(f"✅ Account {acc.id} (Customer {acc.customer_id}):")
                print(f"   - Risk Score: {risk}")
                print(f"   - Z-Score Anomalies: {anomalies}")
                print(f"   - Structuring: {structuring}")
                print(f"   - Velocity Spike: {velocity}")

        print("✅ Analytics Engine test complete")
    finally:
        db.close()

def verify_graph():
    print("\n--- Testing Graph Analysis ---")
    db = SessionLocal()
    try:
        customers = db.query(Customer).all()
        for cust in customers:
            analyzer = GraphAnalyzer(db)
            results = analyzer.build_graph(cust.id)
            
            nodes = len(results.get("nodes", []))
            edges = len(results.get("edges", []))
            communities = len(results.get("communities", []))
            patterns = len(results.get("suspicious_patterns", []))
            
            # Only print interesting graphs
            if nodes > 2:
                print(f"✅ Customer {cust.id} Graph:")
                print(f"   - Nodes: {nodes}, Edges: {edges}")
                print(f"   - Communities: {communities}")
                print(f"   - Suspicious Patterns: {patterns}")
                
        print("✅ Graph Analysis test complete")
    finally:
        db.close()

if __name__ == "__main__":
    verify_analytics()
    verify_graph()
