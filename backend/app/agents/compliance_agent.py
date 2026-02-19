from typing import Dict
from app.agents.base_agent import BaseAgent

class ComplianceAgent(BaseAgent):
    """Agent to validate SAR completeness"""
    
    def execute(self, state: Dict) -> Dict:
        """
        Validate SAR draft against compliance rules.
        
        Returns updated state with compliance_validation.
        """
        
        case_id = state["case_id"]
        sar_draft = state.get("sar_draft", "")
        risk_score = state.get("analytics_results", {}).get("risk_score", 0)
        
        # Validation rules
        validations = {
            "has_narrative": len(sar_draft) > 100,
            "risk_score_present": risk_score > 0,
            "meets_threshold": risk_score >= 0.5,
            "narrative_complete": len(sar_draft.split()) >= 50
        }
        
        all_valid = all(validations.values())
        
        if all_valid:
            recommendation = "FILE_SAR"
        elif validations["meets_threshold"]:
            recommendation = "REVIEW_REQUIRED"
        else:
            recommendation = "NO_ACTION"
        
        output = {
            "validations": validations,
            "recommendation": recommendation,
            "all_valid": all_valid
        }
        
        # Log action
        self.log_action(case_id, {"risk_score": risk_score}, output)
        
        # Update state
        state["compliance_validation"] = output
        state["recommended_action"] = recommendation
        
        return state
