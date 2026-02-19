import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session
from app.models import Transaction, Account

class AnalyticsEngine:
    """AML anomaly detection engine"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def detect_anomalies(self, account_id: int) -> Dict:
        """
        Run all anomaly detection methods on an account.
        
        Returns dict with:
        - z_score_anomalies
        - structuring_detected
        - velocity_spike
        - risk_score
        """
        
        # Get transactions
        transactions = self.db.query(Transaction).filter(
            Transaction.account_id == account_id
        ).order_by(Transaction.timestamp).all()
        
        if not transactions:
            return {
                "anomalies": [],
                "structuring_detected": False,
                "velocity_spike": False,
                "risk_score": 0.0
            }
        # Convert to DataFrame
        df = pd.DataFrame([{
            "id": t.id,
            "amount": float(t.amount),
            "timestamp": t.timestamp,
            "transaction_type": t.transaction_type
        } for t in transactions])
        
        # Clean data
        df["transaction_type"] = df["transaction_type"].str.strip().str.upper()
        
        # Run detection methods
        z_anomalies = self._detect_z_score_anomalies(df)
        structuring = self._detect_structuring(df)
        velocity = self._detect_velocity_spike(df)
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(z_anomalies, structuring, velocity)
        
        return {
            "anomalies": z_anomalies,
            "structuring_detected": structuring,
            "velocity_spike": velocity,
            "risk_score": risk_score
        }
    
    def _detect_z_score_anomalies(self, df: pd.DataFrame) -> List[Dict]:
        """Detect transactions with Z-score > 3"""
        
        mean_amount = df["amount"].mean()
        std_amount = df["amount"].std()
        
        if std_amount == 0:
            return []
        
        df["z_score"] = (df["amount"] - mean_amount) / std_amount
        
        anomalies = df[df["z_score"] > 3].to_dict('records')
        
        return [{"transaction_id": a["id"], "z_score": float(a["z_score"]), "amount": float(a["amount"])} for a in anomalies]
    
    def _detect_structuring(self, df: pd.DataFrame) -> bool:
        """
        Detect structuring: multiple transactions just below $10k within 24 hours.
        """
        
        # Filter deposits/withdrawals near $10k
        near_threshold = df[
            (df["amount"] > 9000) & 
            (df["amount"] < 10000) &
            (df["transaction_type"].isin(["DEPOSIT", "WITHDRAWAL"]))
        ]
        
        if len(near_threshold) < 3:
            return False
        
        # Check if multiple within 24 hours
        near_threshold = near_threshold.sort_values("timestamp")
        
        for i in range(len(near_threshold) - 2):
            window = near_threshold.iloc[i:i+3]
            time_diff = (window.iloc[-1]["timestamp"] - window.iloc[0]["timestamp"]).total_seconds()
            
            if time_diff < 86400:  # 24 hours in seconds
                return True
        
        return False
    
    def _detect_velocity_spike(self, df: pd.DataFrame) -> bool:
        """
        Detect sudden spike in transaction frequency.
        """
        
        # Get recent 7 days
        recent_date = df["timestamp"].max() - timedelta(days=7)
        recent_df = df[df["timestamp"] > recent_date]
        
        if len(recent_df) == 0:
            return False
        
        # Get historical baseline (older than 7 days)
        historical_df = df[df["timestamp"] <= recent_date]
        
        if len(historical_df) < 7:
            return False
        
        # Calculate daily transaction counts
        recent_daily = len(recent_df) / 7
        historical_daily = len(historical_df) / max(1, (df["timestamp"].max() - df["timestamp"].min()).days - 7)
        
        # Spike if recent is 3x historical
        if recent_daily > historical_daily * 3:
            return True
        
        return False
    
    def _calculate_risk_score(self, z_anomalies: List, structuring: bool, velocity: bool) -> float:
        """Calculate overall risk score (0.0 to 1.0)"""
        
        score = 0.0
        
        # Z-score anomalies
        if len(z_anomalies) > 0:
            score += min(0.4, len(z_anomalies) * 0.1)
        
        # Structuring
        if structuring:
            score += 0.4
        
        # Velocity spike
        if velocity:
            score += 0.2
        
        return min(1.0, score)
