"""
RAG Knowledge Base — Stores regulatory guidelines and SAR templates in pgvector.
Uses the existing Embedding model (768-dim) and generate_embedding() from llm.py.
"""
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models import Embedding
from app.llm import generate_embedding

# ─── SYNTHETIC REGULATORY DOCUMENTS ─────────────────────────────────
# These are realistic but synthetic regulatory guidelines and SAR templates.
# In production, these would be ingested from actual FinCEN/BSA documents.

REGULATORY_DOCUMENTS = [
    {
        "type": "regulatory_guideline",
        "title": "BSA/AML Structuring (Smurfing) Guidance",
        "content": """STRUCTURING / SMURFING DETECTION GUIDELINES

Structuring, also known as smurfing, involves breaking up large transactions into multiple 
smaller transactions to evade Currency Transaction Report (CTR) filing requirements. Under 
BSA Section 5324, structuring is a federal offense.

Key indicators of structuring:
1. Multiple cash deposits or withdrawals, each just below the $10,000 CTR threshold
2. Transactions conducted by the same individual or related individuals
3. Deposits made at multiple branches or ATMs within a short timeframe
4. Pattern of transactions in round or near-round amounts below $10,000
5. Customer awareness of reporting thresholds evident from transaction behavior

SAR filing is mandatory when two or more related transactions occur within a 24-hour period 
that individually fall below $10,000 but aggregate above $10,000, and there is no apparent 
business or lawful purpose.

Regulatory reference: 31 CFR 1010.314, FinCEN Advisory FIN-2014-A007"""
    },
    {
        "type": "regulatory_guideline",
        "title": "Money Laundering Layering Techniques",
        "content": """LAYERING DETECTION GUIDELINES

Layering is the second stage of money laundering where illicit funds are separated from 
their source through complex layers of financial transactions. The goal is to make tracing 
the funds back to their criminal origin as difficult as possible.

Key indicators of layering activity:
1. Large deposits immediately followed by multiple wire transfers to unrelated entities
2. Rapid movement of funds through multiple accounts with no apparent business purpose
3. Use of nominees, shell companies, or trusts to obscure beneficial ownership
4. Transactions that mirror or closely match inbound amounts (pass-through behavior)
5. Wire transfers to jurisdictions with weak AML controls or bank secrecy laws
6. Multiple entities receiving similar-sized transfers from a single source

The time between receipt and disbursement is typically very short (same day or within 
48 hours), indicating the account is being used solely as a conduit.

Regulatory reference: FATF ML Typology Report, FinCEN Advisory FIN-2020-A003"""
    },
    {
        "type": "regulatory_guideline",
        "title": "Round-Tripping and Circular Flow Detection",
        "content": """ROUND-TRIPPING DETECTION GUIDELINES

Round-tripping occurs when funds are sent from an account to an external entity and 
subsequently returned to the same or a related account, often through a different channel 
or intermediary. This technique is used to create the appearance of legitimate business 
transactions or to disguise the source of funds.

Key indicators:
1. Outbound transfers followed by inbound deposits of similar amounts within 7-14 days
2. The return path involves a different entity than the original recipient
3. Amounts match within a 10% variance, suggesting coordinated transactions
4. Related counterparty names (e.g., "Corp-Alpha" outbound, "Corp-Alpha-Sub" inbound)
5. No apparent economic purpose for the circular movement of funds
6. Pattern repeats multiple times over weeks or months

Round-tripping is commonly associated with trade-based money laundering, tax evasion, 
and artificial inflation of business revenues.

Regulatory reference: FATF Trade-Based ML Report, FinCEN SAR Activity Review Issue 21"""
    },
    {
        "type": "regulatory_guideline",
        "title": "Rapid Movement and Pass-Through Account Detection",
        "content": """RAPID MOVEMENT / PASS-THROUGH ACCOUNT GUIDELINES

A pass-through account is one where funds are deposited and withdrawn within a very 
short period, typically within the same business day. The account serves merely as a 
conduit, with no legitimate business activity occurring in between.

Key indicators:
1. Large deposits followed by near-identical withdrawals within 24 hours
2. Account maintains low or minimal balance outside of pass-through events
3. Withdrawal amount is 95-100% of deposit amount (minimal funds retained)
4. Counterparties for deposits and withdrawals are typically different entities
5. Pattern occurs repeatedly at regular intervals
6. The account holder has no apparent business need for the volume of transactions

Pass-through behavior is a strong indicator that an account is being used to launder 
proceeds of crime, particularly when combined with offshore wire transfers.

Regulatory reference: FinCEN SAR Narrative Guidance, FFIEC BSA/AML Manual"""
    },
    {
        "type": "regulatory_guideline",
        "title": "Shell Company and Fan-Out Transaction Detection",
        "content": """SHELL COMPANY FAN-OUT DETECTION GUIDELINES

Shell company fan-out involves receiving a large sum into a single account and immediately 
distributing it to numerous entities, many of which may be shell companies with no 
legitimate business operations.

Key indicators:
1. Single large inbound wire transfer followed by 10+ outbound transfers the same day
2. Recipient entities have characteristics of shell companies (generic names, recently formed)
3. Amounts distributed are roughly equal portions of the original inbound amount
4. No business relationship between the account holder and the recipient entities
5. Recipient entities are in multiple jurisdictions
6. The original source of the large inbound wire is unclear or from a high-risk jurisdiction

This pattern is often associated with the placement and layering stages of money laundering, 
where criminal proceeds are rapidly dispersed to make tracing difficult.

Regulatory reference: FATF Guidance on Transparency of Beneficial Ownership, FinCEN Shell Company Advisory"""
    },
    {
        "type": "sar_template",
        "title": "SAR Narrative Template - High Risk Filing",
        "content": """SAR NARRATIVE TEMPLATE — HIGH RISK

SECTION 1: SUBJECT INFORMATION
[Customer name], account number [account], has been identified for suspicious activity 
involving [typology name]. The subject maintains [number] account(s) with the institution.

SECTION 2: SUSPICIOUS ACTIVITY DESCRIPTION
During the review period of [date range], the following suspicious activity was identified:

[Detailed description of the suspicious transactions, including:
- Total number of suspicious transactions
- Aggregate dollar amount
- Date range of activity  
- Specific transaction details (amounts, dates, counterparties)
- Pattern description matching the identified typology]

SECTION 3: REASON FOR SUSPICION
This activity is suspicious because:
- [Specific reason 1, citing transaction data]
- [Specific reason 2, citing regulatory threshold or rule]
- [Specific reason 3, citing behavioral pattern]

The identified pattern is consistent with [typology name] as defined by [regulatory reference].

SECTION 4: INVESTIGATION FINDINGS
Automated analysis revealed:
- Risk Score: [score] out of 1.0
- Anomaly Detection: [z-score findings]
- Network Analysis: [graph analysis findings]
- Typology Match: [matched typology with confidence score]

SECTION 5: RECOMMENDATION
Based on the above findings, this institution recommends [FILE SAR / ESCALATE / REVIEW].

This report was generated with the assistance of an AI-based analysis system. All findings 
have been verified by automated quality checks and are subject to human analyst review."""
    },
    {
        "type": "sar_template",
        "title": "SAR Narrative Template - Escalation Review",
        "content": """SAR NARRATIVE TEMPLATE — REVIEW/ESCALATION

SUBJECT: [Customer name], Account [account number]

ACTIVITY SUMMARY:
Between [start date] and [end date], automated monitoring systems flagged [number] 
transactions totaling approximately [amount] for review. The activity triggered alerts 
for [alert types].

PATTERN DESCRIPTION:
[Description of the transaction pattern that triggered the alert. Include specific 
transaction details, amounts, dates, and counterparty information.]

RISK ASSESSMENT:
- Automated Risk Score: [score]
- Primary Typology Match: [typology] (Confidence: [percentage])
- Network Risk Indicators: [graph analysis summary]

ANALYST NOTES:
[Space for human analyst to add context, additional research findings, 
or justification for filing/not filing decision]

DISPOSITION: [PENDING REVIEW]"""
    },
    {
        "type": "regulatory_guideline",
        "title": "FinCEN SAR Filing Requirements and Narrative Best Practices",
        "content": """FINCEN SAR NARRATIVE BEST PRACTICES

A well-written SAR narrative should:

1. COMPLETENESS: Address the five W's — Who, What, When, Where, and Why
2. CLARITY: Use clear, concise language avoiding jargon or ambiguous terms
3. SPECIFICITY: Include specific transaction amounts, dates, account numbers, and counterparties
4. CONTEXT: Explain why the activity is unusual for the customer's profile
5. OBJECTIVITY: Present facts without speculation or accusatory language
6. TYPOLOGY REFERENCE: Link observed patterns to known money laundering typologies
7. REGULATORY COMPLIANCE: Cite relevant BSA/AML regulations when applicable

Common SAR narrative deficiencies:
- Vague descriptions ("suspicious transactions occurred")
- Missing transaction details (amounts, dates, counterparties)
- No explanation of why the activity is suspicious for THIS customer
- Failure to describe the pattern or typology
- Incomplete subject identification

Filing thresholds:
- Mandatory filing: Transactions involving $5,000+ where a suspect is known
- Mandatory filing: Transactions involving $25,000+ regardless of suspect identification
- Voluntary filing: Any transaction that raises suspicion of money laundering

Regulatory reference: 31 CFR 1020.320, FinCEN SAR Electronic Filing Instructions"""
    },
]


_EMBEDDING_VERSION = 2  # Bump this to force re-seed (v2 = fixed NaN-free embeddings)


class KnowledgeBase:
    """RAG Knowledge Base using pgvector for similarity search"""

    def __init__(self, db: Session):
        self.db = db

    def seed(self):
        """Embed and store all regulatory documents. Re-seeds when embedding version changes."""
        # Always re-seed to ensure embeddings are NaN-free with current algorithm
        existing = self.db.query(Embedding).filter(
            Embedding.content_type.in_(["regulatory_guideline", "sar_template"])
        ).count()

        # Force re-seed: clear old docs and regenerate
        if existing > 0:
            print(f"📚 Clearing {existing} old embeddings (re-seeding with v{_EMBEDDING_VERSION})...")
            self.db.query(Embedding).filter(
                Embedding.content_type.in_(["regulatory_guideline", "sar_template"])
            ).delete()
            self.db.commit()

        count = 0
        for doc in REGULATORY_DOCUMENTS:
            print(f"  Embedding: {doc['title']}...")
            vector = generate_embedding(doc["content"])

            embedding = Embedding(
                content_type=doc["type"],
                content_text=f"[{doc['title']}]\n\n{doc['content']}",
                embedding=vector
            )
            self.db.add(embedding)
            count += 1

        self.db.commit()
        print(f"✅ Seeded {count} documents into knowledge base.")
        return count

    def retrieve_relevant(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Retrieve most relevant documents using cosine similarity via pgvector.

        Args:
            query: The search query (e.g., analytics summary or typology name)
            top_k: Number of results to return

        Returns:
            List of dicts with 'title', 'content', 'similarity' keys
        """
        query_vector = generate_embedding(query)

        # Use pgvector's cosine distance operator
        results = self.db.execute(
            text("""
                SELECT content_text, content_type,
                       1 - (embedding <=> CAST(:query_vec AS vector)) AS similarity
                FROM embeddings
                WHERE content_type IN ('regulatory_guideline', 'sar_template')
                ORDER BY embedding <=> CAST(:query_vec AS vector)
                LIMIT :limit
            """),
            {"query_vec": str(query_vector), "limit": top_k}
        ).fetchall()

        return [
            {
                "content": row[0],
                "type": row[1],
                "similarity": float(row[2])
            }
            for row in results
        ]

    def retrieve_sar_template(self, risk_level: str = "HIGH") -> str:
        """Retrieve the most appropriate SAR template based on risk level."""
        query = f"SAR narrative template for {risk_level} risk filing"
        results = self.retrieve_relevant(query, top_k=1)
        if results:
            return results[0]["content"]
        return ""

    def retrieve_typology_guidance(self, typology_name: str) -> str:
        """Retrieve regulatory guidance for a specific typology."""
        results = self.retrieve_relevant(f"{typology_name} detection guidelines", top_k=1)
        if results:
            return results[0]["content"]
        return ""
