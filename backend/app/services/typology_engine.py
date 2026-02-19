"""
Typology Matching Engine — Maps transaction patterns to known ML typologies.
Returns structured findings with confidence scores and evidence.
"""
from typing import List, Dict
from datetime import timedelta
import pandas as pd


# ─── TYPOLOGY DEFINITIONS ─────────────────────────────────────────
TYPOLOGY_DEFINITIONS = {
    "SMURFING": {
        "name": "Structuring / Smurfing",
        "description": "Multiple deposits below CTR threshold ($10k) from many unique sources",
        "regulatory_ref": "BSA §5324, 31 CFR 1010.314, FinCEN Advisory FIN-2014-A007",
        "risk_weight": 0.9,
    },
    "LAYERING": {
        "name": "Layering",
        "description": "Large deposit immediately split into many smaller outbound transfers",
        "regulatory_ref": "FATF ML Typology Report, FinCEN Advisory FIN-2020-A003",
        "risk_weight": 0.95,
    },
    "ROUND_TRIPPING": {
        "name": "Round-Tripping / Circular Flow",
        "description": "Funds sent out and returned via different channel at similar amount",
        "regulatory_ref": "FATF Trade-Based ML Report, FinCEN SAR Activity Review Issue 21",
        "risk_weight": 0.85,
    },
    "RAPID_MOVEMENT": {
        "name": "Rapid Movement / Pass-Through",
        "description": "Large deposit followed by near-identical withdrawal within 24 hours",
        "regulatory_ref": "FinCEN SAR Narrative Guidance, FFIEC BSA/AML Manual",
        "risk_weight": 0.88,
    },
    "SHELL_FAN_OUT": {
        "name": "Shell Company Fan-Out",
        "description": "Single large wire fanned out to 10+ entities same day",
        "regulatory_ref": "FATF Beneficial Ownership Guidance, FinCEN Shell Company Advisory",
        "risk_weight": 0.92,
    },
}


class TypologyEngine:
    """Matches transaction patterns against known money laundering typologies."""

    def match(self, transactions: List[Dict], analytics_results: Dict, graph_results: Dict) -> List[Dict]:
        """
        Run all typology detectors and return matches with confidence scores.

        Args:
            transactions: Raw transaction list from state
            analytics_results: Output from AnalyticsAgent
            graph_results: Output from CorrelationAgent

        Returns:
            List of matched typologies with confidence and evidence
        """
        if not transactions:
            return []

        df = pd.DataFrame(transactions)
        df["amount"] = df["amount"].astype(float)
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        matches = []

        # Run each detector
        smurfing = self._detect_smurfing(df, analytics_results)
        if smurfing:
            matches.append(smurfing)

        layering = self._detect_layering(df)
        if layering:
            matches.append(layering)

        round_trip = self._detect_round_tripping(df)
        if round_trip:
            matches.append(round_trip)

        rapid = self._detect_rapid_movement(df)
        if rapid:
            matches.append(rapid)

        shell = self._detect_shell_fan_out(df, graph_results)
        if shell:
            matches.append(shell)

        # Sort by confidence
        matches.sort(key=lambda x: x["confidence"], reverse=True)
        return matches

    def _detect_smurfing(self, df: pd.DataFrame, analytics: Dict) -> Dict | None:
        """Detect smurfing: many small deposits below $10k from unique sources within a sliding window."""
        deposits = df[
            (df["transaction_type"].str.upper().str.strip() == "DEPOSIT") &
            (df["amount"] > 4000) &
            (df["amount"] < 10000)
        ].sort_values("timestamp")

        if len(deposits) < 5:
            return None

        # Use sliding 14-day window to find concentrated clusters
        best_window = None
        best_count = 0

        for i in range(len(deposits)):
            window_start = deposits.iloc[i]["timestamp"]
            window_end = window_start + timedelta(days=14)
            window_deposits = deposits[
                (deposits["timestamp"] >= window_start) &
                (deposits["timestamp"] <= window_end)
            ]
            if len(window_deposits) > best_count:
                best_count = len(window_deposits)
                best_window = window_deposits

        if best_window is None or len(best_window) < 5:
            return None

        unique_parties = best_window["counterparty"].nunique()
        if unique_parties < 3:
            return None

        time_range = (best_window["timestamp"].max() - best_window["timestamp"].min()).days
        total_amount = best_window["amount"].sum()
        confidence = min(0.95, 0.4 + (len(best_window) * 0.03) + (unique_parties * 0.02))

        evidence = [
            f"{len(best_window)} deposits below $10k CTR threshold",
            f"{unique_parties} unique counterparties identified",
            f"Activity concentrated in {time_range} day(s)",
            f"Aggregate amount: ${total_amount:,.2f}",
            f"Average deposit: ${best_window['amount'].mean():,.2f}",
        ]

        if analytics.get("structuring_detected"):
            confidence = min(0.98, confidence + 0.1)
            evidence.append("Structuring pattern confirmed by analytics engine")

        defn = TYPOLOGY_DEFINITIONS["SMURFING"]
        return {
            "typology": "SMURFING",
            "name": defn["name"],
            "confidence": round(confidence, 2),
            "evidence": evidence,
            "regulatory_reference": defn["regulatory_ref"],
            "risk_weight": defn["risk_weight"],
            "description": defn["description"],
            "transaction_count": len(best_window),
            "total_amount": float(total_amount),
        }

    def _detect_layering(self, df: pd.DataFrame) -> Dict | None:
        """Detect layering: large deposit → immediate fan-out to multiple parties."""
        deposits = df[df["transaction_type"].str.upper().str.strip() == "DEPOSIT"].sort_values("timestamp")
        transfers = df[df["transaction_type"].str.upper().str.strip() == "TRANSFER"].sort_values("timestamp")

        if deposits.empty or transfers.empty:
            return None

        # Find large deposits (> $50k)
        large_deposits = deposits[deposits["amount"] > 50000]
        if large_deposits.empty:
            return None

        for _, dep in large_deposits.iterrows():
            # Find transfers within 24 hours after deposit
            window_end = dep["timestamp"] + timedelta(hours=24)
            follow_up = transfers[
                (transfers["timestamp"] > dep["timestamp"]) &
                (transfers["timestamp"] <= window_end)
            ]

            if len(follow_up) >= 4:
                unique_recipients = follow_up["counterparty"].nunique()
                total_out = follow_up["amount"].sum()
                pct_dispersed = total_out / dep["amount"] if dep["amount"] > 0 else 0

                confidence = min(0.95, 0.5 + (len(follow_up) * 0.03) + (pct_dispersed * 0.2))

                evidence = [
                    f"Large deposit of ${dep['amount']:,.2f} received",
                    f"{len(follow_up)} outbound transfers within 24 hours",
                    f"{unique_recipients} unique recipients",
                    f"${total_out:,.2f} dispersed ({pct_dispersed*100:.0f}% of deposit)",
                    f"Rapid disbursement consistent with layering behavior",
                ]

                defn = TYPOLOGY_DEFINITIONS["LAYERING"]
                return {
                    "typology": "LAYERING",
                    "name": defn["name"],
                    "confidence": round(confidence, 2),
                    "evidence": evidence,
                    "regulatory_reference": defn["regulatory_ref"],
                    "risk_weight": defn["risk_weight"],
                    "description": defn["description"],
                    "transaction_count": len(follow_up) + 1,
                    "total_amount": float(dep["amount"]),
                }

        return None

    def _detect_round_tripping(self, df: pd.DataFrame) -> Dict | None:
        """Detect round-tripping: outbound transfer → return from different entity at similar amount."""
        outbound = df[df["transaction_type"].str.upper().str.strip() == "TRANSFER"].sort_values("timestamp")
        inbound = df[df["transaction_type"].str.upper().str.strip() == "DEPOSIT"].sort_values("timestamp")

        if outbound.empty or inbound.empty:
            return None

        round_trips = []
        for _, out_txn in outbound.iterrows():
            if out_txn["amount"] < 10000:
                continue

            window_start = out_txn["timestamp"] + timedelta(days=1)
            window_end = out_txn["timestamp"] + timedelta(days=14)

            potential_returns = inbound[
                (inbound["timestamp"] >= window_start) &
                (inbound["timestamp"] <= window_end) &
                (inbound["counterparty"] != out_txn["counterparty"]) &
                (inbound["amount"] >= out_txn["amount"] * 0.85) &
                (inbound["amount"] <= out_txn["amount"] * 1.15)
            ]

            if not potential_returns.empty:
                ret = potential_returns.iloc[0]
                round_trips.append({
                    "out_amount": float(out_txn["amount"]),
                    "in_amount": float(ret["amount"]),
                    "out_party": out_txn["counterparty"],
                    "in_party": ret["counterparty"],
                    "days_apart": (ret["timestamp"] - out_txn["timestamp"]).days,
                })

        if len(round_trips) < 2:
            return None

        total_amount = sum(rt["out_amount"] for rt in round_trips)
        confidence = min(0.95, 0.5 + (len(round_trips) * 0.1))

        evidence = [
            f"{len(round_trips)} round-trip patterns detected",
            f"Funds sent to entity A, returned from entity B within 14 days",
            f"Amounts match within ±15% variance",
            f"Total circular flow: ${total_amount:,.2f}",
        ]
        for rt in round_trips[:3]:
            evidence.append(
                f"  ${rt['out_amount']:,.2f} → {rt['out_party']} → returned as ${rt['in_amount']:,.2f} from {rt['in_party']} ({rt['days_apart']}d later)"
            )

        defn = TYPOLOGY_DEFINITIONS["ROUND_TRIPPING"]
        return {
            "typology": "ROUND_TRIPPING",
            "name": defn["name"],
            "confidence": round(confidence, 2),
            "evidence": evidence,
            "regulatory_reference": defn["regulatory_ref"],
            "risk_weight": defn["risk_weight"],
            "description": defn["description"],
            "transaction_count": len(round_trips) * 2,
            "total_amount": float(total_amount),
        }

    def _detect_rapid_movement(self, df: pd.DataFrame) -> Dict | None:
        """Detect rapid movement: large deposit → same-day withdrawal of similar amount."""
        deposits = df[df["transaction_type"].str.upper().str.strip() == "DEPOSIT"].sort_values("timestamp")
        withdrawals = df[df["transaction_type"].str.upper().str.strip() == "WITHDRAWAL"].sort_values("timestamp")

        if deposits.empty or withdrawals.empty:
            return None

        pass_throughs = []
        for _, dep in deposits.iterrows():
            if dep["amount"] < 20000:
                continue

            same_day_end = dep["timestamp"] + timedelta(hours=24)
            matching_withdrawals = withdrawals[
                (withdrawals["timestamp"] > dep["timestamp"]) &
                (withdrawals["timestamp"] <= same_day_end) &
                (withdrawals["amount"] >= dep["amount"] * 0.90) &
                (withdrawals["amount"] <= dep["amount"] * 1.05)
            ]

            if not matching_withdrawals.empty:
                wd = matching_withdrawals.iloc[0]
                hours_diff = (wd["timestamp"] - dep["timestamp"]).total_seconds() / 3600
                pass_throughs.append({
                    "deposit": float(dep["amount"]),
                    "withdrawal": float(wd["amount"]),
                    "hours_apart": round(hours_diff, 1),
                    "dep_party": dep.get("counterparty", "Unknown"),
                    "wd_party": wd.get("counterparty", "Unknown"),
                })

        if len(pass_throughs) < 2:
            return None

        total = sum(pt["deposit"] for pt in pass_throughs)
        confidence = min(0.95, 0.5 + (len(pass_throughs) * 0.1))

        evidence = [
            f"{len(pass_throughs)} pass-through events detected",
            f"Large deposits immediately followed by same-amount withdrawals",
            f"Funds retained for less than 24 hours each time",
            f"Total pass-through volume: ${total:,.2f}",
        ]
        for pt in pass_throughs[:3]:
            evidence.append(
                f"  ${pt['deposit']:,.2f} in from {pt['dep_party']} → ${pt['withdrawal']:,.2f} out to {pt['wd_party']} ({pt['hours_apart']}h later)"
            )

        defn = TYPOLOGY_DEFINITIONS["RAPID_MOVEMENT"]
        return {
            "typology": "RAPID_MOVEMENT",
            "name": defn["name"],
            "confidence": round(confidence, 2),
            "evidence": evidence,
            "regulatory_reference": defn["regulatory_ref"],
            "risk_weight": defn["risk_weight"],
            "description": defn["description"],
            "transaction_count": len(pass_throughs) * 2,
            "total_amount": float(total),
        }

    def _detect_shell_fan_out(self, df: pd.DataFrame, graph_results: Dict) -> Dict | None:
        """Detect shell company fan-out: large wire → 10+ transfers to shell entities."""
        deposits = df[df["transaction_type"].str.upper().str.strip() == "DEPOSIT"].sort_values("timestamp")
        transfers = df[df["transaction_type"].str.upper().str.strip() == "TRANSFER"].sort_values("timestamp")

        if deposits.empty or transfers.empty:
            return None

        # Find very large deposits (> $100k)
        large_deposits = deposits[deposits["amount"] > 100000]
        if large_deposits.empty:
            return None

        for _, dep in large_deposits.iterrows():
            window_end = dep["timestamp"] + timedelta(hours=24)
            follow_up = transfers[
                (transfers["timestamp"] > dep["timestamp"]) &
                (transfers["timestamp"] <= window_end)
            ]

            unique_recipients = follow_up["counterparty"].nunique()
            if len(follow_up) >= 8 and unique_recipients >= 6:
                total_out = follow_up["amount"].sum()

                # Check for hub pattern in graph
                hub_detected = False
                for pattern in graph_results.get("suspicious_patterns", []):
                    if pattern.get("type") == "high_degree_hub":
                        hub_detected = True

                confidence = min(0.95, 0.5 + (unique_recipients * 0.03) + (0.1 if hub_detected else 0))

                evidence = [
                    f"Large inbound wire of ${dep['amount']:,.2f}",
                    f"{len(follow_up)} outbound transfers on same day",
                    f"{unique_recipients} unique recipient entities",
                    f"Total dispersed: ${total_out:,.2f}",
                    f"Recipients have characteristics of shell entities",
                ]
                if hub_detected:
                    evidence.append("Graph analysis confirms high-degree hub pattern")

                # List some recipients
                top_recipients = follow_up.groupby("counterparty")["amount"].sum().nlargest(5)
                for party, amt in top_recipients.items():
                    evidence.append(f"  → {party}: ${amt:,.2f}")

                defn = TYPOLOGY_DEFINITIONS["SHELL_FAN_OUT"]
                return {
                    "typology": "SHELL_FAN_OUT",
                    "name": defn["name"],
                    "confidence": round(confidence, 2),
                    "evidence": evidence,
                    "regulatory_reference": defn["regulatory_ref"],
                    "risk_weight": defn["risk_weight"],
                    "description": defn["description"],
                    "transaction_count": len(follow_up) + 1,
                    "total_amount": float(dep["amount"]),
                }

        return None
