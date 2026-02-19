from typing import Dict
from app.agents.base_agent import BaseAgent

class IngestionAgent(BaseAgent):
    """Agent to ingest and validate transaction data"""
    
    def execute(self, state: Dict) -> Dict:
        """
        Ingest transaction data and validate structure.
        
        Input state must have:
        - case_id
        - customer_id
        - transactions (list)
        
        Returns updated state with validation results.
        """
        
        case_id = state["case_id"]
        transactions = state.get("transactions", [])
        
        # Validation
        valid_transactions = []
        errors = []
        
        for txn in transactions:
            if self._validate_transaction(txn):
                valid_transactions.append(txn)
            else:
                errors.append(f"Invalid transaction: {txn.get('id', 'unknown')}")
        
        output_data = {
            "valid_count": len(valid_transactions),
            "error_count": len(errors),
            "errors": errors
        }
        
        # Log action
        self.log_action(case_id, {"transaction_count": len(transactions)}, output_data)
        
        # Update state
        state["transactions"] = valid_transactions
        state["ingestion_complete"] = True
        
        return state
    
    def _validate_transaction(self, txn: Dict) -> bool:
        """Validate transaction has required fields"""
        required = ["id", "account_id", "amount", "timestamp"]
        return all(field in txn for field in required)
