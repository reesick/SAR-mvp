import networkx as nx
from typing import List, Dict
from sqlalchemy.orm import Session
from app.models import Transaction, Account

class GraphAnalyzer:
    """Build and analyze transaction graphs"""
    
    def __init__(self, db: Session):
        self.db = db
        self.graph = nx.Graph()
    
    def build_graph(self, customer_id: int) -> Dict:
        """
        Build transaction graph for a customer.
        Nodes = accounts, Edges = transactions between accounts
        """
        
        # Get all accounts for this customer
        accounts = self.db.query(Account).filter(
            Account.customer_id == customer_id
        ).all()
        
        account_ids = [a.id for a in accounts]
        
        # Get all transactions involving these accounts
        transactions = self.db.query(Transaction).filter(
            Transaction.account_id.in_(account_ids)
        ).all()
        
        # Build graph
        for account in accounts:
            self.graph.add_node(str(account.id), account_type=account.account_type)
        
        for txn in transactions:
            # Create edge between account and counterparty
            counterparty_node = f"ext_{txn.counterparty}"
            self.graph.add_node(counterparty_node, account_type="EXTERNAL")
            
            # Ensure source ID is string
            source_node = str(txn.account_id)
            
            self.graph.add_edge(
                source_node,
                counterparty_node,
                weight=float(txn.amount),
                timestamp=txn.timestamp
            )
        
        return self.analyze_graph()
    
    def analyze_graph(self) -> Dict:
        """Analyze graph structure"""
        
        if len(self.graph.nodes) == 0:
            return {
                "nodes": [],
                "edges": [],
                "communities": [],
                "suspicious_patterns": []
            }
        
        # Find communities
        communities = list(nx.community.greedy_modularity_communities(self.graph))
        
        # Find suspicious patterns
        suspicious = []
        
        # Pattern 1: High-degree nodes (transaction hubs)
        degree_dict = dict(self.graph.degree())
        high_degree = [node for node, degree in degree_dict.items() if degree > 10]
        
        if high_degree:
            suspicious.append({
                "type": "high_degree_hub",
                "nodes": high_degree,
                "description": "Accounts with unusually high number of connections"
            })
        
        # Pattern 2: Isolated subgraphs
        if not nx.is_connected(self.graph):
            components = list(nx.connected_components(self.graph))
            isolated = [c for c in components if len(c) > 3]
            
            if isolated:
                suspicious.append({
                    "type": "isolated_community",
                    "nodes": [list(c) for c in isolated],
                    "description": "Isolated transaction communities"
                })
        
        return {
            "nodes": list(self.graph.nodes()),
            "edges": [(u, v, d) for u, v, d in self.graph.edges(data=True)],
            "communities": [list(c) for c in communities],
            "suspicious_patterns": suspicious
        }
