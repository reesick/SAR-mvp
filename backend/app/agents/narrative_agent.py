"""
NarrativeAgent — 3-step Chain-of-Thought SAR narrative generation with RAG.
Each step produces auditable output stored in AgentReasoning.
"""
from typing import Dict
from app.agents.base_agent import BaseAgent
from app.llm import generate_text
from app.services.knowledge_base import KnowledgeBase


class NarrativeAgent(BaseAgent):
    """Agent to generate SAR narrative using multi-step LLM reasoning with RAG context."""

    def execute(self, state: Dict) -> Dict:
        """
        Generate SAR narrative using 3-step chain-of-thought:
          Step 1: Summarize the transaction data and detection findings
          Step 2: Explain WHY this is suspicious, citing typology and regulatory rules
          Step 3: Draft the SAR narrative using a RAG-retrieved template
        """

        case_id = state["case_id"]
        customer_id = state.get("customer_id")
        analytics = state.get("analytics_results", {})
        graph = state.get("graph_results", {})
        typologies = state.get("matched_typologies", [])
        transactions = state.get("transactions", [])

        # ── RAG: Retrieve relevant context ──
        kb = KnowledgeBase(self.db)
        primary_typology = typologies[0] if typologies else None
        typology_name = primary_typology["name"] if primary_typology else "Unknown"

        rag_guidance = kb.retrieve_typology_guidance(typology_name) if primary_typology else ""
        rag_template = kb.retrieve_sar_template(
            "HIGH" if analytics.get("risk_score", 0) > 0.5 else "REVIEW"
        )

        rag_context = [
            {"type": "typology_guidance", "content": rag_guidance[:1500]},
            {"type": "sar_template", "content": rag_template[:1500]},
        ]

        # ── Build transaction summary for prompts ──
        txn_summary = self._summarize_transactions(transactions)

        # ═══════════════════════════════════════════════════
        # STEP 1: DATA SUMMARY
        # ═══════════════════════════════════════════════════
        step1_prompt = f"""You are an AML data analyst. Summarize the following financial data concisely.

CUSTOMER ID: {customer_id}

TRANSACTION DATA:
{txn_summary}

ANOMALY DETECTION RESULTS:
- Risk Score: {analytics.get('risk_score', 0):.2f}
- Z-Score Anomalies Found: {len(analytics.get('anomalies', []))}
- Structuring Detected: {analytics.get('structuring_detected', False)}
- Velocity Spike: {analytics.get('velocity_spike', False)}

NETWORK ANALYSIS:
- Suspicious Patterns: {len(graph.get('suspicious_patterns', []))}
- Communities Detected: {len(graph.get('communities', []))}
- Total Network Nodes: {len(graph.get('nodes', []))}

MATCHED TYPOLOGIES:
{self._format_typologies(typologies)}

Produce a clear 3-4 paragraph factual summary of this data. Do NOT make recommendations yet.
Focus on: what transactions occurred, amounts, counterparties, timing, and which anomalies were flagged."""

        step1_output = generate_text(step1_prompt)

        # Store Step 1 reasoning
        self.store_reasoning(case_id, {
            "step": "1_data_summary",
            "prompt": step1_prompt,
            "output": step1_output,
            "output_length": len(step1_output)
        }, [])

        # ═══════════════════════════════════════════════════
        # STEP 2: REASONING — WHY IS THIS SUSPICIOUS?
        # ═══════════════════════════════════════════════════
        step2_prompt = f"""You are a senior AML compliance investigator. Based on the data summary below,
explain WHY this activity is suspicious. Cite specific evidence.

DATA SUMMARY:
{step1_output}

MATCHED TYPOLOGY: {typology_name}
TYPOLOGY CONFIDENCE: {primary_typology['confidence'] if primary_typology else 'N/A'}

REGULATORY GUIDANCE:
{rag_guidance[:1000]}

EVIDENCE FROM DETECTION ENGINE:
{self._format_evidence(primary_typology)}

Your task:
1. Explain what specific transactions or patterns are suspicious
2. Why they match the identified typology ({typology_name})
3. Which regulatory rules or thresholds are potentially violated
4. What the likely intent or purpose of the activity might be

Write 3-4 paragraphs. Be specific — cite transaction amounts, dates, counterparties.
Use professional, objective language. Do not speculate beyond the facts."""

        step2_output = generate_text(step2_prompt)

        # Store Step 2 reasoning
        self.store_reasoning(case_id, {
            "step": "2_reasoning",
            "prompt": step2_prompt,
            "output": step2_output,
            "typology_matched": typology_name,
            "output_length": len(step2_output)
        }, [])

        # ═══════════════════════════════════════════════════
        # STEP 3: SAR DRAFT — Formal regulatory narrative
        # ═══════════════════════════════════════════════════
        step3_prompt = f"""You are writing a Suspicious Activity Report (SAR) for a US financial institution.
Use the following template structure and reasoning to produce the final narrative.

SAR TEMPLATE:
{rag_template[:1200]}

DATA SUMMARY:
{step1_output}

INVESTIGATOR'S REASONING:
{step2_output}

CASE DETAILS:
- Case ID: {case_id[:8]}
- Customer ID: {customer_id}
- Risk Score: {analytics.get('risk_score', 0):.2f}
- Primary Typology: {typology_name}
- Regulatory Reference: {primary_typology.get('regulatory_reference', 'N/A') if primary_typology else 'N/A'}

Write a complete, ready-to-file SAR narrative following the template structure.
Include all 5 sections: Subject Info, Suspicious Activity, Reason for Suspicion, 
Investigation Findings, and Recommendation.

Be specific with transaction amounts, dates, and counterparties.
Use formal, regulatory-compliant language.
Length: 400-600 words."""

        step3_output = generate_text(step3_prompt)

        # Store Step 3 reasoning
        self.store_reasoning(case_id, {
            "step": "3_sar_draft",
            "prompt": step3_prompt,
            "output_length": len(step3_output),
            "rag_template_used": bool(rag_template),
            "rag_guidance_used": bool(rag_guidance)
        }, [])

        # ── Log action ──
        self.log_action(
            case_id,
            {
                "method": "3-Step Chain-of-Thought with RAG",
                "typology_matched": typology_name,
                "rag_documents_retrieved": len([c for c in rag_context if c["content"]]),
            },
            {
                "step1_length": len(step1_output),
                "step2_length": len(step2_output),
                "step3_length": len(step3_output),
            }
        )

        # ── Update state ──
        state["sar_draft"] = step3_output
        state["rag_context"] = rag_context
        state["reasoning_chain"] = [
            {"step": 1, "title": "Data Summary", "output": step1_output},
            {"step": 2, "title": "Reasoning Analysis", "output": step2_output},
            {"step": 3, "title": "SAR Narrative Draft", "output": step3_output},
        ]
        state["narrative_reasoning_id"] = 0  # Updated by store_reasoning

        return state

    def _summarize_transactions(self, transactions: list) -> str:
        """Create a concise text summary of transactions for the LLM."""
        if not transactions:
            return "No transactions available."

        total = sum(float(t.get("amount", 0)) for t in transactions)
        types = {}
        counterparties = set()
        for t in transactions:
            tt = t.get("transaction_type", "UNKNOWN")
            types[tt] = types.get(tt, 0) + 1
            counterparties.add(t.get("counterparty", "Unknown"))

        lines = [
            f"Total transactions: {len(transactions)}",
            f"Total volume: ${total:,.2f}",
            f"Transaction types: {', '.join(f'{k}: {v}' for k, v in types.items())}",
            f"Unique counterparties: {len(counterparties)}",
            "",
            "LARGEST TRANSACTIONS:",
        ]

        sorted_txns = sorted(transactions, key=lambda x: float(x.get("amount", 0)), reverse=True)
        for t in sorted_txns[:10]:
            lines.append(
                f"  ${float(t['amount']):,.2f} | {t.get('transaction_type', '?')} | "
                f"{t.get('counterparty', '?')} | {t.get('timestamp', '?')[:16]} | {t.get('description', '')}"
            )

        return "\n".join(lines)

    def _format_typologies(self, typologies: list) -> str:
        """Format matched typologies for prompt."""
        if not typologies:
            return "No specific typology matched."

        lines = []
        for t in typologies:
            lines.append(f"- {t['name']} (Confidence: {t['confidence']:.0%})")
            for e in t.get("evidence", [])[:3]:
                lines.append(f"    • {e}")
        return "\n".join(lines)

    def _format_evidence(self, typology: dict | None) -> str:
        """Format evidence from a typology match."""
        if not typology:
            return "No specific evidence available."

        lines = []
        for e in typology.get("evidence", []):
            lines.append(f"• {e}")
        return "\n".join(lines)
