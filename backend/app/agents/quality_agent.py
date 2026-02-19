"""
QualityAgent — Reviews the SAR draft for completeness, accuracy, and regulatory compliance.
Uses LLM to perform self-critique and assigns a quality score.
"""
from typing import Dict
from app.agents.base_agent import BaseAgent
from app.llm import generate_text


SAR_CHECKLIST = [
    "Subject identification (customer name or ID)",
    "Account information referenced",
    "Suspicious activity clearly described",
    "Specific transaction amounts cited",
    "Transaction dates or timeframes mentioned",
    "Counterparty information included",
    "Reason for suspicion explicitly stated",
    "Typology or pattern named",
    "Regulatory reference or threshold cited",
    "Recommendation (FILE/REVIEW/ESCALATE) stated",
    "Professional and objective tone maintained",
    "No speculative or accusatory language",
]


class QualityAgent(BaseAgent):
    """Agent that reviews the SAR draft for quality, completeness, and compliance."""

    def execute(self, state: Dict) -> Dict:
        """
        Review the SAR draft against a completeness checklist using the LLM.

        Returns updated state with quality_score and quality_issues.
        """

        case_id = state["case_id"]
        sar_draft = state.get("sar_draft", "")
        risk_score = state.get("analytics_results", {}).get("risk_score", 0)
        typologies = state.get("matched_typologies", [])
        primary_typology = typologies[0]["name"] if typologies else "Unknown"

        if not sar_draft or len(sar_draft) < 50:
            state["quality_score"] = 0
            state["quality_issues"] = ["SAR draft is empty or too short"]
            self.log_action(case_id, {"draft_length": len(sar_draft)}, {"quality_score": 0})
            return state

        # ── Build review prompt ──
        checklist_text = "\n".join(f"{i+1}. {item}" for i, item in enumerate(SAR_CHECKLIST))

        review_prompt = f"""You are a senior AML compliance reviewer conducting a quality check on a SAR narrative.

SAR NARRATIVE TO REVIEW:
---
{sar_draft}
---

CASE CONTEXT:
- Risk Score: {risk_score:.2f}
- Primary Typology: {primary_typology}

QUALITY CHECKLIST — Evaluate each item as PASS or FAIL:
{checklist_text}

INSTRUCTIONS:
1. For each checklist item, write "PASS" or "FAIL" followed by a brief reason
2. At the end, provide:
   - QUALITY SCORE: [0-100] based on how many items pass and overall quality
   - CRITICAL ISSUES: List any critical problems that MUST be fixed
   - SUGGESTIONS: List any improvements that would strengthen the narrative

Format your response EXACTLY as:
CHECKLIST:
1. [PASS/FAIL] - [reason]
2. [PASS/FAIL] - [reason]
...

QUALITY_SCORE: [number]
CRITICAL_ISSUES: [list or "None"]
SUGGESTIONS: [list or "None"]"""

        review_output = generate_text(review_prompt)

        # ── Parse quality score ──
        quality_score = self._parse_quality_score(review_output)
        quality_issues = self._parse_issues(review_output)

        # ── If quality is low, attempt to improve ──
        improved_draft = sar_draft
        if quality_score < 60 and len(quality_issues) > 0:
            improved_draft = self._improve_draft(sar_draft, quality_issues, primary_typology, risk_score)

        # ── Store reasoning ──
        reasoning = {
            "method": "LLM SAR Quality Review",
            "checklist_items": len(SAR_CHECKLIST),
            "quality_score": quality_score,
            "issues_found": len(quality_issues),
            "draft_improved": improved_draft != sar_draft,
            "review_output": review_output,
        }
        self.store_reasoning(case_id, reasoning, [])

        # ── Log action ──
        self.log_action(
            case_id,
            {"draft_length": len(sar_draft), "risk_score": risk_score},
            {
                "quality_score": quality_score,
                "issues": quality_issues[:5],
                "improved": improved_draft != sar_draft
            }
        )

        # ── Update state ──
        if improved_draft != sar_draft:
            state["sar_draft"] = improved_draft
        state["quality_score"] = quality_score
        state["quality_issues"] = quality_issues

        return state

    def _parse_quality_score(self, review_output: str) -> int:
        """Extract quality score from LLM output."""
        try:
            for line in review_output.split("\n"):
                if "QUALITY_SCORE" in line.upper() or "QUALITY SCORE" in line.upper():
                    # Extract number from the line
                    parts = line.split(":")
                    if len(parts) >= 2:
                        score_text = parts[-1].strip().split("/")[0].strip()
                        # Remove any non-digit characters
                        score_digits = ''.join(c for c in score_text if c.isdigit())
                        if score_digits:
                            return min(100, max(0, int(score_digits)))
        except Exception:
            pass

        # Fallback: count PASS items
        pass_count = review_output.upper().count("PASS")
        return min(100, int((pass_count / max(1, len(SAR_CHECKLIST))) * 100))

    def _parse_issues(self, review_output: str) -> list:
        """Extract critical issues from LLM output."""
        issues = []
        in_issues = False

        for line in review_output.split("\n"):
            line = line.strip()
            if "CRITICAL_ISSUES" in line.upper() or "CRITICAL ISSUES" in line.upper():
                in_issues = True
                # Check if issues are on the same line
                parts = line.split(":", 1)
                if len(parts) > 1 and parts[1].strip().lower() != "none":
                    issues.append(parts[1].strip())
                continue
            if "SUGGESTIONS" in line.upper():
                in_issues = False
                continue
            if in_issues and line and line.lower() != "none":
                # Clean up list markers
                cleaned = line.lstrip("- •*").strip()
                if cleaned:
                    issues.append(cleaned)

        # Also capture FAIL items
        for line in review_output.split("\n"):
            if "FAIL" in line.upper() and "CHECKLIST" not in line.upper():
                parts = line.split("-", 1)
                if len(parts) > 1:
                    reason = parts[1].strip()
                    if reason and reason not in issues:
                        issues.append(f"Failed check: {reason}")

        return issues[:10]  # Cap at 10

    def _improve_draft(self, original_draft: str, issues: list, typology: str, risk_score: float) -> str:
        """Attempt to improve the SAR draft based on identified issues."""

        issues_text = "\n".join(f"- {issue}" for issue in issues[:5])

        improve_prompt = f"""You are a SAR narrative editor. The following draft SAR was reviewed and found deficient.
Fix the identified issues while preserving the core content.

ORIGINAL DRAFT:
---
{original_draft}
---

ISSUES TO FIX:
{issues_text}

CONTEXT:
- Typology: {typology}
- Risk Score: {risk_score:.2f}

Write an IMPROVED version of the SAR narrative that addresses all the issues above.
Keep the same structure and length (400-600 words). Make it regulatory-compliant."""

        improved = generate_text(improve_prompt)

        # Sanity check — only use improved version if it's reasonable
        if len(improved) > 100 and not improved.startswith("Error"):
            return improved
        return original_draft
