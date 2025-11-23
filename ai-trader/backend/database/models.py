# SQLAlchemy Database Models for AI Trading System
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, ForeignKey, Enum, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class SignalStatus(str, enum.Enum):
    """Signal processing status"""
    RECEIVED = "received"
    VALIDATED = "validated"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"


class SignalDirection(str, enum.Enum):
    """Signal direction - alias for TradeDirection"""
    BUY = "buy"
    SELL = "sell"


class TradeStatus(str, enum.Enum):
    """Trade lifecycle status"""
    PENDING = "pending"
    PLACED = "placed"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class TradeDirection(str, enum.Enum):
    """Trade direction"""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, enum.Enum):
    """MT5 order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class UserRole(str, enum.Enum):
    """User roles for access control"""
    ADMIN = "admin"
    TRADER = "trader"
    VIEWER = "viewer"


class User(Base):
    """User model for authentication"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    
    # Role and status
    role = Column(Enum(UserRole), default=UserRole.TRADER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships
    settings = relationship("UserSettings", back_populates="user", uselist=False)
    
    __table_args__ = (
        Index('idx_user_username', 'username'),
        Index('idx_user_email', 'email'),
    )


class Signal(Base):
    """Raw signals from TradingView webhooks"""
    __tablename__ = 'signals'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Signal data
    symbol = Column(String(20), nullable=False, index=True)
    direction = Column(Enum(TradeDirection), nullable=False)
    timeframe = Column(String(10))  # 1m, 5m, 15m, 1h, 4h, 1d
    strategy_name = Column(String(100))
    
    # Price levels
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    
    # Metadata
    raw_payload = Column(JSON)  # Store entire webhook payload
    source_ip = Column(String(50))
    
    # Processing status
    status = Column(Enum(SignalStatus), default=SignalStatus.RECEIVED, nullable=False, index=True)
    rejection_reason = Column(Text)

    # Institutional Data (New)
    targets = Column(JSON)  # [TP1, TP2, TP3]
    confidence = Column(JSON)  # ["Reason 1", "Reason 2"]
    volatility = Column(String(20))  # Low, Medium, High
    win_probability = Column(Float)  # 0-100
    
    # Relationships
    prediction = relationship("Prediction", back_populates="signal", uselist=False)
    trade = relationship("Trade", back_populates="signal", uselist=False)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_signal_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_signal_status_timestamp', 'status', 'timestamp'),
    )


class Prediction(Base):
    """AI model predictions for signals"""
    __tablename__ = 'predictions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(Integer, ForeignKey('signals.id'), unique=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Model information
    model_name = Column(String(100), nullable=False)  # lstm_v1, transformer_v2, lightgbm_v3
    model_version = Column(String(50), nullable=False)
    
    # Prediction outputs
    prediction = Column(Float, nullable=False)  # -1 to 1 or probability
    confidence = Column(Float, nullable=False)  # 0 to 1
    expected_return = Column(Float)  # Expected % return
    
    # LLM confirmation (new)
    llm_approved = Column(Boolean)  # LLM approval decision
    llm_reasoning = Column(Text)  # Natural language explanation from LLM
    llm_confidence = Column(Float)  # LLM confidence score
    
    # Feature values (for debugging)
    features = Column(JSON)
    
    # Performance
    inference_time_ms = Column(Float)
    
    # Relationships
    signal = relationship("Signal", back_populates="prediction")
    
    __table_args__ = (
        Index('idx_prediction_model', 'model_name', 'timestamp'),
    )


class Trade(Base):
    """Complete trade lifecycle from signal to close"""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(Integer, ForeignKey('signals.id'), unique=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Trade details
    symbol = Column(String(20), nullable=False, index=True)
    direction = Column(Enum(TradeDirection), nullable=False)
    order_type = Column(Enum(OrderType), default=OrderType.MARKET, nullable=False)
    
    # MT5 order information
    mt5_order_id = Column(String(50), index=True)  # Ticket number from MT5
    mt5_position_id = Column(String(50), index=True)
    
    # Execution details
    requested_lots = Column(Float, nullable=False)
    executed_lots = Column(Float)
    entry_price_requested = Column(Float)
    entry_price_filled = Column(Float)
    slippage_points = Column(Float)
    
    # Risk management
    stop_loss = Column(Float)
    take_profit = Column(Float)
    risk_amount = Column(Float)  # Dollar amount at risk
    risk_percent = Column(Float)  # % of account
    
    # Position status
    status = Column(Enum(TradeStatus), default=TradeStatus.PENDING, nullable=False, index=True)
    
    # Close details
    exit_price = Column(Float)
    close_timestamp = Column(DateTime)
    lots_closed = Column(Float)
    
    # P&L
    gross_pnl = Column(Float)  # Before commission
    commission = Column(Float)
    swap = Column(Float)
    net_pnl = Column(Float)  # Final profit/loss
    
    # Trade duration
    duration_seconds = Column(Integer)
    
    # Metadata
    rejection_reason = Column(Text)
    error_message = Column(Text)
    
    # Relationships
    signal = relationship("Signal", back_populates="trade")
    
    __table_args__ = (
        Index('idx_trade_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_trade_status', 'status', 'timestamp'),
        Index('idx_trade_mt5_order', 'mt5_order_id'),
    )


class Position(Base):
    """Current open positions snapshot"""
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    mt5_position_id = Column(String(50), unique=True, nullable=False, index=True)
    last_update = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Position details
    symbol = Column(String(20), nullable=False, index=True)
    direction = Column(Enum(TradeDirection), nullable=False)
    lots = Column(Float, nullable=False)
    
    # Price information
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    
    # P&L
    unrealized_pnl = Column(Float)
    swap = Column(Float, default=0)
    commission = Column(Float, default=0)
    
    # Trade reference
    trade_id = Column(Integer, ForeignKey('trades.id'))
    
    # Timestamps
    open_timestamp = Column(DateTime, nullable=False)
    
    __table_args__ = (
        Index('idx_position_symbol', 'symbol'),
    )


class RiskMetrics(Base):
    """Daily risk and performance metrics"""
    __tablename__ = 'risk_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, unique=True, index=True)
    
    # Account metrics
    balance = Column(Float, nullable=False)
    equity = Column(Float, nullable=False)
    margin_used = Column(Float)
    margin_free = Column(Float)
    margin_level = Column(Float)  # %
    
    # Daily performance
    daily_pnl = Column(Float)
    daily_return_pct = Column(Float)
    trades_count = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float)
    
    # Risk metrics
    max_drawdown_pct = Column(Float)
    current_drawdown_pct = Column(Float)
    sharpe_ratio = Column(Float)
    sortino_ratio = Column(Float)
    
    # Exposure
    total_exposure = Column(Float)  # Total position value
    exposure_by_symbol = Column(JSON)  # {"EURUSD": 10000, "XAUUSD": 5000}
    
    # Circuit breaker status
    daily_loss_limit_hit = Column(Boolean, default=False)
    consecutive_losses = Column(Integer, default=0)
    kill_switch_active = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ModelVersion(Base):
    """Deployed ML model versions"""
    __tablename__ = 'model_versions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Model identification
    model_name = Column(String(100), nullable=False)  # lstm, transformer, lightgbm
    version = Column(String(50), nullable=False)
    model_path = Column(String(500))  # S3 path or local path
    
    # Deployment status
    is_active = Column(Boolean, default=False, index=True)
    deployed_at = Column(DateTime)
    deprecated_at = Column(DateTime)
    
    # Training metadata
    training_date = Column(DateTime)
    training_samples = Column(Integer)
    validation_accuracy = Column(Float)
    validation_sharpe = Column(Float)
    
    # Hyperparameters
    hyperparameters = Column(JSON)
    
    # Performance tracking
    live_accuracy = Column(Float)
    live_trades_count = Column(Integer, default=0)
    live_win_rate = Column(Float)
    
    # Configuration
    feature_config = Column(JSON)  # Which features to use
    
    __table_args__ = (
        Index('idx_model_active', 'is_active', 'model_name'),
    )


class AuditLog(Base):
    """Security and compliance audit trail"""
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Event details
    event_type = Column(String(100), nullable=False, index=True)  # signal_received, trade_executed, kill_switch_activated
    user_id = Column(String(100))  # For dashboard actions
    ip_address = Column(String(50))
    
    # Context
    entity_type = Column(String(50))  # signal, trade, model
    entity_id = Column(Integer)
    
    # Details
    action = Column(String(100), nullable=False)  # create, update, delete, execute
    details = Column(JSON)
    
    # Result
    success = Column(Boolean, nullable=False)
    error_message = Column(Text)
    
    __table_args__ = (
        Index('idx_audit_event_timestamp', 'event_type', 'timestamp'),
    )


class SystemHealth(Base):
    """System health checks and status"""
    __tablename__ = 'system_health'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Service status
    webhook_service_healthy = Column(Boolean, default=True)
    ai_service_healthy = Column(Boolean, default=True)
    risk_service_healthy = Column(Boolean, default=True)
    execution_service_healthy = Column(Boolean, default=True)
    
    # MT5 connection
    mt5_connected = Column(Boolean, default=True)
    mt5_account_number = Column(String(50))
    mt5_server = Column(String(100))
    
    # Database
    database_connected = Column(Boolean, default=True)
    database_latency_ms = Column(Float)
    
    # Redis
    redis_connected = Column(Boolean, default=True)
    redis_latency_ms = Column(Float)
    
    # System resources
    cpu_usage_pct = Column(Float)
    memory_usage_pct = Column(Float)
    disk_usage_pct = Column(Float)
    
    # Alerts
    active_alerts = Column(JSON)  # List of current issues

class UserSettings(Base):
    """User preferences and configuration"""
    __tablename__ = 'user_settings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False, index=True)
    
    # Timezone preferences
    timezone = Column(String(50), default='UTC', nullable=False)
    
    # MT5 Configuration (encrypted)
    mt5_login = Column(String(100))
    mt5_password = Column(String(255))  # Will be encrypted
    mt5_server = Column(String(100))
    mt5_enabled = Column(Boolean, default=False)
    
    # Display preferences
    show_sessions = Column(Boolean, default=True)
    default_chart_timeframe = Column(String(10), default='1H')
    theme = Column(String(20), default='dark')
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship("User", back_populates="settings")
    
    __table_args__ = (
        Index('idx_user_settings_user', 'user_id'),
    )
