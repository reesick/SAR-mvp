from typing import Dict
from app.agents.base_agent import BaseAgent
from app.services.graph_analysis import GraphAnalyzer

class CorrelationAgent(BaseAgent):
    """Agent to build and analyze transaction graphs"""
    
    def execute(self, state: Dict) -> Dict:
        """
        Build transaction graph and find patterns.
        
        Returns updated state with graph_results.
        """
        
        case_id = state["case_id"]
        customer_id = state.get("customer_id")
        
        if not customer_id:
            state["graph_results"] = {"error": "No customer_id provided"}
            return state
        
        # Build graph
        analyzer = GraphAnalyzer(self.db)
        graph_results = analyzer.build_graph(customer_id)
        
        # Store reasoning
        reasoning = {
            "method": "NetworkX Graph Analysis",
            "community_count": len(graph_results["communities"]),
            "suspicious_patterns": graph_results["suspicious_patterns"],
            "suspicious_pattern_count": len(graph_results["suspicious_patterns"])
        }
        
        reasoning_id = self.store_reasoning(case_id, reasoning, [str(customer_id)])
        
        # Log action
        self.log_action(
            case_id,
            {"customer_id": customer_id},
            {"pattern_count": len(graph_results["suspicious_patterns"])}
        )
        
        # Update state
        state["graph_results"] = graph_results
        state["correlation_reasoning_id"] = reasoning_id
        
        return state
