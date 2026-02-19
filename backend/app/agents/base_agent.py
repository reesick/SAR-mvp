from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models import AuditLog, AgentReasoning
from datetime import datetime
import logging

logger = logging.getLogger("aml.agents")

class BaseAgent:
    """Base class for all agents"""
    
    def __init__(self, db: Session):
        self.db = db
        self.agent_name = self.__class__.__name__
    
    def log_action(self, case_id: str, input_data: Dict, output_data: Dict):
        """Log agent action to audit table"""
        logger.info(f"  ▸ {self.agent_name} → logging action to audit trail")
        
        audit_log = AuditLog(
            case_id=case_id,
            action_type=f"{self.agent_name}_execution",
            agent_name=self.agent_name,
            input_data=input_data,
            output_data=output_data
        )
        self.db.add(audit_log)
        self.db.commit()
        
        return audit_log.id
    
    def store_reasoning(self, case_id: str, reasoning: Dict, data_refs: List[str]):
        """Store agent reasoning"""
        step = reasoning.get("step", "")
        logger.info(f"  ▸ {self.agent_name} → storing reasoning{' (' + step + ')' if step else ''}")
        
        reasoning_record = AgentReasoning(
            case_id=case_id,
            agent_name=self.agent_name,
            reasoning_json=reasoning,
            data_references=data_refs
        )
        self.db.add(reasoning_record)
        self.db.commit()
        
        return reasoning_record.id

    def execute(self, state: Dict) -> Dict:
        """Override in subclass"""
        raise NotImplementedError

