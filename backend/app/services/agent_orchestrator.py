"""
AgentOrchestrator — LangGraph pipeline for multi-agent SAR generation.
7-node pipeline: Ingestion → Analytics → Correlation → Narrative → Quality → Compliance → Audit
"""
from typing import Dict, TypedDict, List
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session
import logging

from app.agents.ingestion_agent import IngestionAgent
from app.agents.analytics_agent import AnalyticsAgent
from app.agents.correlation_agent import CorrelationAgent
from app.agents.narrative_agent import NarrativeAgent
from app.agents.quality_agent import QualityAgent
from app.agents.compliance_agent import ComplianceAgent
from app.agents.audit_logger import AuditLogger

logger = logging.getLogger("aml.pipeline")


def _run_node(name, agent_cls, db, state):
    """Wrapper that logs each pipeline node execution."""
    logger.info(f"━━━ [{name.upper()}] starting ━━━")
    result = agent_cls(db).execute(state)
    logger.info(f"    [{name.upper()}] ✓ done")
    return result


class AgentState(TypedDict):
    """Full state schema for the agent pipeline."""
    # ── Core identifiers ──
    case_id: str
    customer_id: int

    # ── Data ──
    transactions: List[Dict]

    # ── Analytics outputs ──
    analytics_results: Dict
    matched_typologies: List[Dict]  # NEW: from TypologyEngine
    analytics_reasoning_id: int

    # ── Graph / Correlation outputs ──
    graph_results: Dict
    correlation_reasoning_id: int

    # ── RAG context ──
    rag_context: List[Dict]  # NEW: retrieved regulatory docs

    # ── Narrative outputs ──
    sar_draft: str
    reasoning_chain: List[Dict]  # NEW: 3-step CoT outputs
    narrative_reasoning_id: int

    # ── Quality review outputs ──
    quality_score: int  # NEW: 0-100
    quality_issues: List[str]  # NEW: issues found

    # ── Compliance outputs ──
    compliance_validation: Dict
    recommended_action: str

    # ── Audit ──
    risk_score: float
    reasoning_steps: List[Dict]
    data_references: List[str]
    audit_log_id: int
    ingestion_complete: bool
    audit_complete: bool


class AgentOrchestrator:
    """LangGraph orchestrator for multi-agent SAR generation.

    Pipeline:
        Ingestion → Analytics (+ Typology) → Correlation (Graph) →
        Narrative (3-step CoT + RAG) → Quality Review → Compliance → Audit
    """

    def __init__(self, db: Session):
        self.db = db
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build LangGraph state machine with 7 agent nodes."""

        workflow = StateGraph(AgentState)

        # ── Add nodes (each wrapped with logging) ──
        db = self.db
        workflow.add_node("ingestion",      lambda state: _run_node("ingestion", IngestionAgent, db, state))
        workflow.add_node("analytics",      lambda state: _run_node("analytics", AnalyticsAgent, db, state))
        workflow.add_node("correlation",    lambda state: _run_node("correlation", CorrelationAgent, db, state))
        workflow.add_node("narrative",      lambda state: _run_node("narrative", NarrativeAgent, db, state))
        workflow.add_node("quality_review", lambda state: _run_node("quality_review", QualityAgent, db, state))
        workflow.add_node("compliance",     lambda state: _run_node("compliance", ComplianceAgent, db, state))
        workflow.add_node("audit",          lambda state: _run_node("audit", AuditLogger, db, state))

        # ── Define edges ──
        workflow.set_entry_point("ingestion")
        workflow.add_edge("ingestion",      "analytics")
        workflow.add_edge("analytics",      "correlation")
        workflow.add_edge("correlation",    "narrative")
        workflow.add_edge("narrative",      "quality_review")
        workflow.add_edge("quality_review", "compliance")
        workflow.add_edge("compliance",     "audit")
        workflow.add_edge("audit",          END)

        return workflow.compile()

    def run(self, initial_state: Dict) -> Dict:
        """
        Run the full 7-agent pipeline.

        Args:
            initial_state: Must contain case_id, customer_id, transactions

        Returns:
            Final state with SAR draft, risk score, quality score, audit trail
        """

        # Ensure all new state fields have defaults
        defaults = {
            "matched_typologies": [],
            "rag_context": [],
            "reasoning_chain": [],
            "quality_score": 0,
            "quality_issues": [],
        }

        for key, default in defaults.items():
            if key not in initial_state:
                initial_state[key] = default

        final_state = self.graph.invoke(initial_state)
        return final_state
