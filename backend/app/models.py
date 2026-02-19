from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, DECIMAL
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    account_number = Column(String(50), unique=True)
    risk_profile = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    account_type = Column(String(50))
    balance = Column(DECIMAL(15, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    amount = Column(DECIMAL(15, 2), nullable=False)
    transaction_type = Column(String(50))
    timestamp = Column(DateTime(timezone=True), nullable=False)
    counterparty = Column(String(255))
    description = Column(Text)

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    alert_type = Column(String(100))
    severity = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved = Column(Boolean, default=False)

class GraphEdge(Base):
    __tablename__ = "graph_edges"
    
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, nullable=False)
    target_id = Column(Integer, nullable=False)
    edge_type = Column(String(50))
    weight = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Embedding(Base):
    __tablename__ = "embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    content_type = Column(String(50))
    content_id = Column(Integer)
    content_text = Column(Text)
    embedding = Column(Vector(768))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SARReport(Base):
    __tablename__ = "sar_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String(100), unique=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    report_text = Column(Text)
    risk_score = Column(Float)
    status = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    version = Column(Integer, default=1)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String(100))
    action_type = Column(String(100))
    agent_name = Column(String(100))
    input_data = Column(JSONB)
    output_data = Column(JSONB)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class AgentReasoning(Base):
    __tablename__ = "agent_reasoning"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String(100))
    agent_name = Column(String(100))
    reasoning_json = Column(JSONB)
    data_references = Column(JSONB)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
