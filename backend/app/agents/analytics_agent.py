"""
AnalyticsAgent — Runs anomaly detection on all customer accounts, 
then matches results against known money laundering typologies.
"""
from typing import Dict
from app.agents.base_agent import BaseAgent
from app.services.analytics import AnalyticsEngine
from app.services.typology_engine import TypologyEngine


class AnalyticsAgent(BaseAgent):
    """Agent to detect anomalies and match money laundering typologies."""

    def __init__(self, db):
        super().__init__(db)
        self.analytics = AnalyticsEngine(db)
        self.typology_engine = TypologyEngine()

    def execute(self, state: Dict) -> Dict:
        """
        Run anomaly detection + typology matching on transactions.

        Returns updated state with analytics_results and matched_typologies.
        """

        case_id = state["case_id"]
        transactions = state.get("transactions", [])

        if not transactions:
            state["analytics_results"] = {"error": "No transactions to analyze"}
            state["matched_typologies"] = []
            return state

        # ── Step 1: Anomaly detection on each account ──
        account_ids = list(set(txn["account_id"] for txn in transactions))

        aggregated_results = {
            "anomalies": [],
            "structuring_detected": False,
            "velocity_spike": False,
            "risk_score": 0.0,
            "account_breakdown": {},
            "accounts_analyzed": len(account_ids),
        }

        for acc_id in account_ids:
            results = self.analytics.detect_anomalies(acc_id)

            if results["structuring_detected"]:
                aggregated_results["structuring_detected"] = True
            if results["velocity_spike"]:
                aggregated_results["velocity_spike"] = True

            aggregated_results["anomalies"].extend(results["anomalies"])

            if results["risk_score"] > aggregated_results["risk_score"]:
                aggregated_results["risk_score"] = results["risk_score"]

            aggregated_results["account_breakdown"][acc_id] = results

        # ── Step 2: Typology matching ──
        # Graph results may not be available yet (CorrelationAgent runs after us)
        # So we pass empty graph results and typology engine handles it
        graph_results = state.get("graph_results", {})
        matched_typologies = self.typology_engine.match(
            transactions, aggregated_results, graph_results
        )

        # Boost risk score if a high-confidence typology is matched
        if matched_typologies:
            best_match = matched_typologies[0]
            typology_risk = best_match["risk_weight"] * best_match["confidence"]
            aggregated_results["risk_score"] = min(
                1.0,
                max(aggregated_results["risk_score"], typology_risk)
            )

        # ── Store reasoning ──
        reasoning = {
            "method": "Multi-Account Analysis + Typology Matching",
            "accounts_analyzed": account_ids,
            "anomaly_count": len(aggregated_results["anomalies"]),
            "structuring": aggregated_results["structuring_detected"],
            "velocity_spike": aggregated_results["velocity_spike"],
            "base_risk_score": aggregated_results["risk_score"],
            "typologies_matched": [
                {
                    "typology": t["typology"],
                    "confidence": t["confidence"],
                    "evidence_count": len(t.get("evidence", [])),
                }
                for t in matched_typologies
            ],
        }

        data_refs = [str(txn["id"]) for txn in transactions]
        reasoning_id = self.store_reasoning(case_id, reasoning, data_refs)

        # ── Log action ──
        self.log_action(
            case_id,
            {
                "accounts_analyzed": len(account_ids),
                "transaction_count": len(transactions),
            },
            {
                "risk_score": aggregated_results["risk_score"],
                "anomaly_count": len(aggregated_results["anomalies"]),
                "structuring": aggregated_results["structuring_detected"],
                "velocity_spike": aggregated_results["velocity_spike"],
                "typologies_matched": [t["typology"] for t in matched_typologies],
                "top_confidence": matched_typologies[0]["confidence"] if matched_typologies else 0,
            }
        )

        # ── Update state ──
        state["analytics_results"] = aggregated_results
        state["matched_typologies"] = matched_typologies
        state["analytics_reasoning_id"] = reasoning_id

        return state
