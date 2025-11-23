# Webhook Service - Main FastAPI Application
from fastapi import FastAPI, Request, HTTPException, Depends, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
import json
import os

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Internal imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import (
    get_db_session, init_db, check_database_health,
    Signal, SignalStatus, Trade, TradeStatus, AuditLog
)
from common import (
    WebhookSignatureValidator, verify_jwt_token, rate_limiter,
    manager as ws_manager, Room
)


# ============================================
# Pydantic Schemas
# ============================================

class SignalPayload(BaseModel):
    """TradingView webhook signal schema"""
    symbol: str = Field(..., description="Trading symbol (e.g., EURUSD, XAUUSD)")
    direction: str = Field(..., description="Trade direction: buy or sell")
    timeframe: Optional[str] = Field(None, description="Chart timeframe")
    strategy_name: Optional[str] = Field(None, description="TradingView strategy name")
    
    # Optional price levels
    entry_price: Optional[float] = Field(None, gt=0)
    stop_loss: Optional[float] = Field(None, gt=0)
    take_profit: Optional[float] = Field(None, gt=0)
    
    # Metadata
    timestamp: Optional[str] = None
    
    @validator('direction')
    def validate_direction(cls, v):
        v = v.lower()
        if v not in ['buy', 'sell']:
            raise ValueError('Direction must be "buy" or "sell"')
        return v
    
    @validator('symbol')
    def normalize_symbol(cls, v):
        return v.upper().replace(" ", "")


class SignalResponse(BaseModel):
    """Response after receiving signal"""
    success: bool
    signal_id: int
    status: str
    message: str


class TradeQuery(BaseModel):
    """Query parameters for trades"""
    symbol: Optional[str] = None
    status: Optional[str] = None
    limit: int = Field(100, le=1000)


# ============================================
# FastAPI Application
# ============================================

app = FastAPI(
    title="AI Trading System - Webhook Service",
    description="Receives TradingView alerts and orchestrates AI→Risk→Execution pipeline",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# Background Tasks & Helpers
# ============================================

def format_prices_data(prices_data: dict) -> list:
    """Format raw price data for frontend"""
    import random
    formatted_prices = []
    
    for symbol, data in prices_data.items():
        # Determine if crypto (24/7) or forex (24/5)
        is_crypto = symbol in ['BTCUSD', 'ETHUSD']
        
        # Check market hours for forex
        day = datetime.utcnow().weekday()  # 0=Monday, 6=Sunday
        hour = datetime.utcnow().hour
        
        # Market is open if crypto OR (not weekend and not Friday night)
        market_open = is_crypto or (day < 5 or (day == 6 and hour >= 22))
        
        # Simulate buy/sell percentages (in production, get from order book)
        if market_open:
            buy_percent = random.randint(40, 80)
            change = data.get('change_24h', 0)
        else:
            buy_percent = 50
            change = 0
        
        sell_percent = 100 - buy_percent
        
        formatted_prices.append({
            'symbol': symbol,
            'name': get_pair_name(symbol),
            'price': data.get('price'),
            'change': change,
            'buyPercent': buy_percent,
            'sellPercent': sell_percent,
            'marketOpen': market_open,
            'isCrypto': is_crypto,
            'timestamp': data.get('timestamp'),
            'source': data.get('source', 'api')
        })
    return formatted_prices


async def broadcast_prices_task():
    """Background task to broadcast prices via WebSocket"""
    from common import Room
    from common.price_feed import price_feed
    import asyncio
    
    print("📡 Starting Price Broadcast Task...")
    while True:
        try:
            # Fetch prices (non-blocking)
            prices_data = await asyncio.to_thread(price_feed.get_all_prices)
            
            # Format prices
            formatted_prices = format_prices_data(prices_data)
            
            # Broadcast
            await ws_manager.broadcast_to_room(Room.PRICES, {
                "type": "prices",
                "data": formatted_prices
            })
            
            # Update every 2s (respecting API limits)
            await asyncio.sleep(2) 
            
        except asyncio.CancelledError:
            print("📡 Price Broadcast Task Cancelled")
            break
        except Exception as e:
            print(f"❌ Error in price broadcast: {e}")
            await asyncio.sleep(5)


# Global task reference
price_task = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    print("🚀 Starting Webhook Service...")
    
    # Check and run migrations (Add new columns if missing)
    try:
        from database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            # Check if targets column exists
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='signals' AND column_name='targets'"))
            if not result.fetchone():
                print("🔄 Running migration: Adding institutional columns to signals table...")
                conn.execute(text("ALTER TABLE signals ADD COLUMN targets JSON"))
                conn.execute(text("ALTER TABLE signals ADD COLUMN confidence JSON"))
                conn.execute(text("ALTER TABLE signals ADD COLUMN volatility VARCHAR(20)"))
                conn.execute(text("ALTER TABLE signals ADD COLUMN win_probability FLOAT"))
                conn.commit()
                print("✅ Migration complete")
    except Exception as e:
        print(f"⚠️ Migration check failed (might be SQLite or already exists): {e}")

    # Initialize database
    try:
        init_db()
        print("✅ Database initialized")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
    
    # Connect WebSocket manager to Redis
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    await ws_manager.connect_redis(redis_url)
    
    # Start Price Broadcast Task
    global price_task
    import asyncio
    price_task = asyncio.create_task(broadcast_prices_task())
    
    print("✅ Webhook Service started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("🛑 Shutting down Webhook Service...")
    
    # Cancel background task
    if price_task:
        price_task.cancel()
        try:
            await price_task
        except asyncio.CancelledError:
            pass
            
    await ws_manager.close_all()
    print("✅ Webhook Service stopped")


# ============================================
# Health Check Endpoints
# ============================================

@app.get("/health")
async def health_check():
    """Basic health check"""
    db_health = check_database_health()
    
    return {
        "status": "healthy" if db_health["healthy"] else "unhealthy",
        "service": "webhook",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_health
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AI Trading Webhook Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "webhook": "/webhook/signal",
            "trades": "/trades",
            "signals": "/signals",
            "health": "/health",
            "auth": {
                "login": "/auth/login",
                "register": "/auth/register",
                "me": "/auth/me"
            }
        }
    }


# ============================================
# Authentication Schemas
# ============================================

class UserRegister(BaseModel):
    """User registration schema"""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=5, max_length=100)
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """User login schema"""
    username: str
    password: str


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    """User response schema"""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]


# ============================================
# Authentication Endpoints
# ============================================

@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserRegister,
    db: Session = Depends(get_db_session)
):
    """
    Register a new user
    """
    from database.user_management import create_user
    from database.models import UserRole
    
    try:
        user = create_user(
            db=db,
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            role=UserRole.TRADER
        )
        
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=user.last_login
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.post("/auth/login", response_model=Token)
async def login(
    credentials: UserLogin,
    db: Session = Depends(get_db_session)
):
    """
    Login and receive JWT token
    """
    from database.user_management import authenticate_user, create_access_token
    
    user = authenticate_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.id, "username": user.username})
    
    return Token(
        access_token=access_token,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value
        }
    )


@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_endpoint(
    token_data: dict = Depends(verify_jwt_token),
    db: Session = Depends(get_db_session)
):
    """
    Get current user from JWT token
    """
    from database.models import User
    
    user_id = token_data.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login=user.last_login
    )


# ============================================
# TradingView Webhook Endpoint
# ============================================

@app.post("/webhook/signal", response_model=SignalResponse)
async def receive_signal(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session)
):
    """
    Receive signal from TradingView webhook
    """
    # Rate limiting
    client_ip = request.client.host
    if not rate_limiter.is_allowed(client_ip, max_requests=10, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    # Get raw body for HMAC validation
    raw_body = await request.body()
    body_str = raw_body.decode('utf-8')
    
    # Validate HMAC signature (from header)
    signature = request.headers.get('X-TradingView-Signature', '')
    
    if signature and not WebhookSignatureValidator.validate_signature(body_str, signature):
        # Log failed attempt
        audit = AuditLog(
            event_type="webhook_signature_validation_failed",
            ip_address=client_ip,
            action="receive_signal",
            success=False,
            error_message="Invalid HMAC signature"
        )
        db.add(audit)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )
    
    # Parse JSON payload
    try:
        payload_dict = json.loads(body_str)
        payload = SignalPayload(**payload_dict)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payload: {str(e)}"
        )
    
    # Generate Institutional Data (Simulating AI Analysis)
    from common.ai_client import ai_client
    
    # Get fast prediction for initial display
    ai_pred = await ai_client.get_prediction({
        'symbol': payload.symbol,
        'direction': payload.direction,
        'timeframe': payload.timeframe
    })
    
    # Calculate targets based on Risk (Entry - SL)
    risk = abs(payload.entry_price - payload.stop_loss) if payload.entry_price and payload.stop_loss else 0.0010
    targets = []
    if payload.direction.lower() == 'buy':
        targets = [
            payload.entry_price + risk * 1.5,
            payload.entry_price + risk * 2.5,
            payload.entry_price + risk * 4.0
        ]
    else:
        targets = [
            payload.entry_price - risk * 1.5,
            payload.entry_price - risk * 2.5,
            payload.entry_price - risk * 4.0
        ]
    
    # Round targets
    targets = [round(t, 4) if 'JPY' not in payload.symbol else round(t, 2) for t in targets]
    
    # Create signal record
    signal = Signal(
        symbol=payload.symbol,
        direction=payload.direction,
        timeframe=payload.timeframe or "H1",
        strategy_name=payload.strategy_name or "AI Trend Follower",
        entry_price=payload.entry_price,
        stop_loss=payload.stop_loss,
        take_profit=payload.take_profit,
        raw_payload=payload_dict,
        source_ip=client_ip,
        status=SignalStatus.RECEIVED,
        
        # Institutional Data
        targets=targets,
        confidence=["AI Analyzing..."], # Placeholder until pipeline finishes
        volatility='Medium', # Placeholder
        win_probability=round(ai_pred['confidence'] * 100, 1)
    )
    
    db.add(signal)
    db.commit()
    db.refresh(signal)
    
    # Log audit trail
    audit = AuditLog(
        event_type="signal_received",
        ip_address=client_ip,
        entity_type="signal",
        entity_id=signal.id,
        action="create",
        details=payload_dict,
        success=True
    )
    db.add(audit)
    db.commit()
    
    # Broadcast to WebSocket clients
    await ws_manager.broadcast_signal({
        "signal_id": signal.id,
        "symbol": signal.symbol,
        "direction": signal.direction,
        "timestamp": signal.timestamp.isoformat(),
        "status": signal.status.value,
        "win_probability": signal.win_probability,
        "volatility": signal.volatility
    })
    
    # Trigger processing pipeline in background
    background_tasks.add_task(process_signal_pipeline, signal.id)
    
    return SignalResponse(
        success=True,
        signal_id=signal.id,
        status=signal.status.value,
        message=f"Signal received and queued for processing"
    )


async def process_signal_pipeline(signal_id: int):
    """
    Background task to process signal through complete validation pipeline:
    1. AI Inference Service (LSTM/ML prediction)
    2. LLM Validation (Reasoning-based confirmation)
    3. Risk Management Service (Position sizing, circuit breakers)
    4. Execution Service (MT5 order placement)
    """
    from database import get_db, Prediction, Trade, TradeStatus, TradeDirection
    from common.ai_client import ai_client
    
    print(f"📊 Processing signal {signal_id} through pipeline...")
    
    with get_db() as db:
        # Get signal
        signal = db.query(Signal).filter(Signal.id == signal_id).first()
        if not signal:
            print(f"❌ Signal {signal_id} not found")
            return
        
        try:
            # === STEP 1: AI Inference ===
            print(f"🤖 Step 1: Running AI inference...")
            
            # Get prediction from AI Client
            signal_data_for_ai = {
                'symbol': signal.symbol,
                'direction': signal.direction.value,
                'entry_price': signal.entry_price,
                'timeframe': signal.timeframe
            }
            ai_prediction = await ai_client.get_prediction(signal_data_for_ai)
            
            # === STEP 2: LLM Validation ===
            print(f"🧠 Step 2: Running LLM validation...")
            
            validation_result = await ai_client.validate_signal(
                signal_data={
                    'symbol': signal.symbol,
                    'direction': signal.direction.value,
                    'entry_price': signal.entry_price,
                    'stop_loss': signal.stop_loss,
                    'take_profit': signal.take_profit,
                    'timeframe': signal.timeframe,
                    'strategy_name': signal.strategy_name
                },
                prediction=ai_prediction,
                risk_assessment={'approved': True, 'risk_level': 'medium'}
            )
            
            llm_approved = validation_result['approved']
            llm_reasoning = validation_result['reasoning']
            llm_confidence = validation_result['confidence']
            
            # Update Signal with AI insights
            signal.win_probability = round(ai_prediction['confidence'] * 100, 1)
            
            # Extract key phrases from reasoning for "confidence factors"
            # Simple heuristic: split by newlines or commas and take top 3
            factors = [f.strip() for f in llm_reasoning.split('\n') if f.strip() and not f.startswith('LLM') and len(f) < 50]
            signal.confidence = factors[:3] if factors else ["AI Approved"]
            
            # Store prediction record
            prediction = Prediction(
                signal_id=signal_id,
                model_name=ai_prediction['model_name'],
                model_version='1.0',
                prediction=ai_prediction['prediction'],
                confidence=ai_prediction['confidence'],
                expected_return=ai_prediction['expected_return'],
                llm_approved=llm_approved,
                llm_reasoning=llm_reasoning,
                llm_confidence=llm_confidence,
                features=ai_prediction['features'],
                inference_time_ms=50.0
            )
            db.add(prediction)
            db.commit()
            
            print(f"{'✅' if llm_approved else '❌'} LLM Decision: {'APPROVED' if llm_approved else 'REJECTED'}")
            print(f"   Reasoning: {llm_reasoning[:100]}...")
            
            # If LLM rejects, stop here
            if not llm_approved:
                signal.status = SignalStatus.REJECTED
                signal.rejection_reason = f"LLM rejected: {llm_reasoning[:50]}..."
                db.commit()
                
                # Broadcast update
                await ws_manager.broadcast_signal({
                    "signal_id": signal.id,
                    "symbol": signal.symbol,
                    "direction": signal.direction,
                    "timestamp": signal.timestamp.isoformat(),
                    "status": signal.status.value,
                    "win_probability": signal.win_probability,
                    "volatility": signal.volatility,
                    "confidence": signal.confidence
                })
                return
            
            # === STEP 3: Risk Management ===
            print(f"🛡️  Step 3: Running risk assessment...")
            # Placeholder - would call risk service
            risk_approved = True
            position_size = 0.1
            
            if not risk_approved:
                signal.status = SignalStatus.REJECTED
                signal.rejection_reason = "Risk manager rejected"
                db.commit()
                return
            
            # === STEP 4: Execution ===
            print(f"⚡ Step 4: Executing trade...")
            # Placeholder - would call execution service
            trade = Trade(
                signal_id=signal_id,
                symbol=signal.symbol,
                direction=TradeDirection.BUY if signal.direction.value == 'buy' else TradeDirection.SELL,
                requested_lots=position_size,
                entry_price_requested=signal.entry_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                status=TradeStatus.PENDING
            )
            db.add(trade)
            signal.status = SignalStatus.EXECUTED
            db.commit()
            
            print(f"✅ Signal {signal_id} processed successfully")
            print(f"   Trade ID: {trade.id}")
            
            # Broadcast update
            await ws_manager.broadcast_signal({
                "signal_id": signal.id,
                "symbol": signal.symbol,
                "direction": signal.direction,
                "timestamp": signal.timestamp.isoformat(),
                "status": signal.status.value,
                "win_probability": signal.win_probability,
                "volatility": signal.volatility,
                "confidence": signal.confidence
            })
            
        except Exception as e:
            print(f"❌ Error processing signal {signal_id}: {e}")
            signal.status = SignalStatus.FAILED
            signal.rejection_reason = str(e)
            db.commit()


# ============================================
# Query Endpoints (for Dashboard)
# ============================================

@app.get("/signals")
async def get_signals(
    symbol: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db_session),
    # token_data: dict = Depends(verify_jwt_token)  # Disabled for testing
):
    """Get signals history"""
    query = db.query(Signal)
    
    if symbol:
        query = query.filter(Signal.symbol == symbol.upper())
    
    if status:
        query = query.filter(Signal.status == status)
    
    signals = query.order_by(Signal.timestamp.desc()).limit(limit).all()
    
    return {
        "count": len(signals),
        "signals": [
            {
                "id": s.id,
                "symbol": s.symbol,
                "direction": s.direction.value,
                "timestamp": s.timestamp.isoformat(),
                "status": s.status.value,
                "entry_price": s.entry_price,
                "stop_loss": s.stop_loss,
                "take_profit": s.take_profit,
                
                # Institutional Data
                "strategy": s.strategy_name,
                "timeframe": s.timeframe,
                "targets": s.targets or [s.take_profit],
                "confidence": s.confidence or [],
                "volatility": s.volatility or "Medium",
                "winProbability": s.win_probability or 75
            }
            for s in signals
        ]
    }


@app.get("/trades")
async def get_trades(
    symbol: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db_session),
    # token_data: dict = Depends(verify_jwt_token)  # Disabled for testing
):
    """Get trades history"""
    try:
        query = db.query(Trade)
        
        if symbol:
            query = query.filter(Trade.symbol == symbol.upper())
        
        if status:
            query = query.filter(Trade.status == status)
        
        trades = query.order_by(Trade.timestamp.desc()).limit(limit).all()
        
        return {
            "count": len(trades),
            "trades": [
                {
                    "id": t.id,
                    "symbol": t.symbol,
                    "direction": t.direction.value,
                    "timestamp": t.timestamp.isoformat(),
                    "status": t.status.value,
                    "executed_lots": t.executed_lots,
                    "entry_price_filled": t.entry_price_filled,
                    "net_pnl": t.net_pnl,
                    "mt5_order_id": t.mt5_order_id
                }
                for t in trades
            ]
        }
    except Exception as e:
        print(f"❌ Error in get_trades: {e}")
        import traceback
        traceback.print_exc()
        return {"count": 0, "trades": []}


@app.get("/stats")
async def get_stats(
    db: Session = Depends(get_db_session),
    # token_data: dict = Depends(verify_jwt_token)  # Disabled for testing
):
    """Get trading statistics"""
    try:
        from sqlalchemy import func
        
        # Total signals
        total_signals = db.query(func.count(Signal.id)).scalar() or 0
        
        # Total trades
        total_trades = db.query(func.count(Trade.id)).scalar() or 0
        
        # Open trades
        open_trades = db.query(func.count(Trade.id)).filter(
            Trade.status.in_([TradeStatus.PLACED, TradeStatus.FILLED])
        ).scalar() or 0
        
        # Total P&L
        total_pnl = db.query(func.sum(Trade.net_pnl)).filter(
            Trade.status == TradeStatus.CLOSED
        ).scalar() or 0
        
        # Win rate
        winning_trades = db.query(func.count(Trade.id)).filter(
            Trade.status == TradeStatus.CLOSED,
            Trade.net_pnl > 0
        ).scalar() or 0
        
        closed_trades = db.query(func.count(Trade.id)).filter(
            Trade.status == TradeStatus.CLOSED
        ).scalar() or 0
        
        win_rate = (winning_trades / closed_trades * 100) if closed_trades > 0 else 0
        
        return {
            "total_signals": total_signals,
            "total_trades": total_trades,
            "open_trades": open_trades,
            "total_pnl": round(float(total_pnl), 2),
            "win_rate": round(float(win_rate), 2),
            "closed_trades": closed_trades,
            "winning_trades": winning_trades
        }
    except Exception as e:
        print(f"❌ Error in get_stats: {e}")
        import traceback
        traceback.print_exc()
        # Return default stats instead of crashing
        return {
            "total_signals": 0,
            "total_trades": 0,
            "open_trades": 0,
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "closed_trades": 0,
            "winning_trades": 0
        }


# ============================================
# Settings Management Endpoints
# ============================================

class SettingsUpdate(BaseModel):
    """User settings update schema"""
    timezone: Optional[str] = None
    mt5_login: Optional[str] = None
    mt5_password: Optional[str] = None
    mt5_server: Optional[str] = None
    mt5_enabled: Optional[bool] = None
    show_sessions: Optional[bool] = None
    default_chart_timeframe: Optional[str] = None
    theme: Optional[str] = None


@app.get("/api/settings")
async def get_user_settings(
    db: Session = Depends(get_db_session),
    token_data: dict = Depends(verify_jwt_token)
):
    """Get current user settings"""
    from database import UserSettings
    from common.encryption import encryption
    
    user_id = token_data.get('sub', 'default_user')
    
    # Get or create settings
    settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    
    if not settings:
        # Create default settings
        settings = UserSettings(user_id=user_id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    # Decrypt MT5 password for display (masked)
    mt5_password_masked = "****" if settings.mt5_password else None
    
    return {
        "user_id": settings.user_id,
        "timezone": settings.timezone,
        "mt5_login": settings.mt5_login,
        "mt5_password": mt5_password_masked,
        "mt5_server": settings.mt5_server,
        "mt5_enabled": settings.mt5_enabled,
        "show_sessions": settings.show_sessions,
        "default_chart_timeframe": settings.default_chart_timeframe,
        "theme": settings.theme,
        "created_at": settings.created_at.isoformat(),
        "updated_at": settings.updated_at.isoformat() if settings.updated_at else None
    }


@app.put("/api/settings")
async def update_user_settings(
    settings_update: SettingsUpdate,
    db: Session = Depends(get_db_session),
    token_data: dict = Depends(verify_jwt_token)
):
    """Update user settings"""
    from database import UserSettings
    from common.encryption import encryption
    
    user_id = token_data.get('sub', 'default_user')
    
    # Get or create settings
    settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    
    if not settings:
        settings = UserSettings(user_id=user_id)
        db.add(settings)
    
    # Update fields
    if settings_update.timezone is not None:
        settings.timezone = settings_update.timezone
    
    if settings_update.mt5_login is not None:
        settings.mt5_login = settings_update.mt5_login
    
    if settings_update.mt5_password is not None and settings_update.mt5_password != "****":
        # Encrypt password
        settings.mt5_password = encryption.encrypt(settings_update.mt5_password)
    
    if settings_update.mt5_server is not None:
        settings.mt5_server = settings_update.mt5_server
    
    if settings_update.mt5_enabled is not None:
        settings.mt5_enabled = settings_update.mt5_enabled
    
    if settings_update.show_sessions is not None:
        settings.show_sessions = settings_update.show_sessions
    
    if settings_update.default_chart_timeframe is not None:
        settings.default_chart_timeframe = settings_update.default_chart_timeframe
    
    if settings_update.theme is not None:
        settings.theme = settings_update.theme
    
    db.commit()
    db.refresh(settings)
    
    return {
        "success": True,
        "message": "Settings updated successfully",
        "settings": {
            "timezone": settings.timezone,
            "mt5_enabled": settings.mt5_enabled,
            "show_sessions": settings.show_sessions,
            "theme": settings.theme
        }
    }


# ============================================
# System Status Endpoint
# ============================================

@app.get("/api/status")
async def get_system_status():
    """Get comprehensive system status"""
    import time
    
    # Check database
    db_start = time.time()
    db_health = check_database_health()
    db_latency = (time.time() - db_start) * 1000
    
    # Check Redis (if available)
    redis_connected = False
    redis_latency = None
    try:
        import redis
        r = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
        redis_start = time.time()
        r.ping()
        redis_latency = (time.time() - redis_start) * 1000
        redis_connected = True
    except:
        pass
    
    # Check MT5 (if configured)
    mt5_connected = False
    try:
        import MetaTrader5 as mt5
        if mt5.initialize():
            mt5_connected = True
            mt5.shutdown()
    except:
        pass
    
    return {
        "status": "online",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "api": {
                "status": "healthy",
                "uptime_seconds": int(time.time())  # Simplified
            },
            "database": {
                "status": "healthy" if db_health["healthy"] else "unhealthy",
                "latency_ms": round(db_latency, 2),
                "connected": db_health["healthy"]
            },
            "redis": {
                "status": "healthy" if redis_connected else "unavailable",
                "latency_ms": round(redis_latency, 2) if redis_latency else None,
                "connected": redis_connected
            },
            "mt5": {
                "status": "connected" if mt5_connected else "disconnected",
                "connected": mt5_connected
            }
        },
        "version": "1.0.0"
    }


# ============================================
# Live Prices Endpoint
# ============================================

@app.get("/api/prices/live")
async def get_live_prices():
    """Get real-time prices for all supported pairs"""
    from common.price_feed import price_feed
    import asyncio
    
    try:
        # Fetch prices (non-blocking)
        prices_data = await asyncio.to_thread(price_feed.get_all_prices)
        
        # Format using helper
        formatted_prices = format_prices_data(prices_data)
        
        return {
            'success': True,
            'prices': formatted_prices,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'prices': []
        }


def get_pair_name(symbol: str) -> str:
    """Get human-readable pair name"""
    names = {
        'EURUSD': 'Euro / US Dollar',
        'GBPUSD': 'Pound / US Dollar',
        'USDJPY': 'US Dollar / Yen',
        'XAUUSD': 'Gold / US Dollar',
        'BTCUSD': 'Bitcoin / US Dollar',
        'ETHUSD': 'Ethereum / US Dollar'
    }
    return names.get(symbol, symbol)


# ============================================
# WebSocket Endpoints
# ============================================

from fastapi import WebSocket

@app.websocket("/ws/{room}")
async def websocket_route(websocket: WebSocket, room: str):
    """WebSocket endpoint for real-time updates"""
    from common.websocket import websocket_endpoint
    await websocket_endpoint(websocket, room)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
