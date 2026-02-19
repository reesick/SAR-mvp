"""Quick test to isolate pipeline errors."""
from app.database import SessionLocal
from app.models import Transaction, Account
from app.services.analytics import AnalyticsEngine
from app.services.typology_engine import TypologyEngine
from app.services.knowledge_base import KnowledgeBase
import json

db = SessionLocal()

try:
    # Test 1: Get customer data
    accs = db.query(Account).filter(Account.customer_id == 11).all()
    acc_ids = [a.id for a in accs]
    print(f"[1] Accounts for Customer 11: {acc_ids}")

    txns = db.query(Transaction).filter(Transaction.account_id.in_(acc_ids)).all()
    print(f"[2] Transactions: {len(txns)}")

    # Test 2: Analytics
    eng = AnalyticsEngine(db)
    for a in accs:
        r = eng.detect_anomalies(a.id)
        print(f"[3] Account {a.id}: risk={r['risk_score']}, struct={r['structuring_detected']}")

    # Test 3: Typology Engine
    txn_dicts = [{
        "id": t.id, "account_id": t.account_id, "amount": float(t.amount),
        "transaction_type": t.transaction_type, "timestamp": t.timestamp.isoformat(),
        "counterparty": t.counterparty, "description": t.description
    } for t in txns]

    te = TypologyEngine()
    matches = te.match(txn_dicts, r, {})
    print(f"[4] Typology matches: {len(matches)}")
    for m in matches:
        print(f"    {m['typology']}: confidence={m['confidence']}")

    # Test 4: Knowledge Base
    kb = KnowledgeBase(db)
    results = kb.retrieve_relevant("smurfing structuring detection", top_k=2)
    print(f"[5] RAG results: {len(results)}")
    for r in results:
        print(f"    Type: {r['type']}, Similarity: {r['similarity']:.3f}")

    # Test 5: Full pipeline
    print("\n[6] Running full pipeline...")
    from app.services.agent_orchestrator import AgentOrchestrator
    import uuid

    orchestrator = AgentOrchestrator(db)
    initial = {
        "case_id": str(uuid.uuid4()),
        "customer_id": 11,
        "transactions": txn_dicts,
        "analytics_results": {},
        "graph_results": {},
        "sar_draft": "",
        "risk_score": 0.0,
        "reasoning_steps": [],
        "data_references": [],
        "audit_log_id": 0,
        "matched_typologies": [],
        "rag_context": [],
        "reasoning_chain": [],
        "quality_score": 0,
        "quality_issues": [],
    }

    result = orchestrator.run(initial)
    print(f"\n[7] PIPELINE COMPLETE!")
    print(f"    Risk Score: {result.get('analytics_results', {}).get('risk_score')}")
    print(f"    Typologies: {[t['typology'] for t in result.get('matched_typologies', [])]}")
    print(f"    SAR Length: {len(result.get('sar_draft', ''))}")
    print(f"    Quality Score: {result.get('quality_score')}")
    print(f"    Recommendation: {result.get('recommended_action')}")

except Exception as e:
    import traceback
    print(f"\n❌ ERROR: {e}")
    traceback.print_exc()

finally:
    db.close()
