from typing import Dict
from app.agents.base_agent import BaseAgent

class AuditLogger(BaseAgent):
    """Agent to finalize audit trail"""
    
    def execute(self, state: Dict) -> Dict:
        """
        Finalize audit trail for the case.
        
        Returns updated state with audit_log_id.
        """
        
        case_id = state["case_id"]
        
        # Collect all reasoning IDs
        reasoning_ids = [
            state.get("analytics_reasoning_id"),
            state.get("correlation_reasoning_id"),
            state.get("narrative_reasoning_id")
        ]
        
        reasoning_ids = [r for r in reasoning_ids if r]
        
        # Create final audit summary
        audit_summary = {
            "case_id": case_id,
            "reasoning_ids": reasoning_ids,
            "risk_score": state.get("analytics_results", {}).get("risk_score", 0),
            "recommendation": state.get("recommended_action", "UNKNOWN"),
            "complete": True
        }
        
        # Log final action
        audit_log_id = self.log_action(case_id, {}, audit_summary)
        
        # Update state
        state["audit_log_id"] = audit_log_id
        state["audit_complete"] = True
        
        return state
