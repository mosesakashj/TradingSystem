# Risk Management Engine
from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum
import os


class RiskLevel(str, Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskConfig:
    """Risk management configuration"""
    # Daily limits
    daily_loss_limit_pct: float = 2.0  # % of account equity
    daily_profit_target_pct: float = 5.0  # Optional profit target
    
    # Position sizing
    max_position_size_pct: float = 5.0  # % of account per trade
    max_total_exposure_pct: float = 30.0  # Total exposure across all positions
    
    # Consecutive losses
    max_consecutive_losses: int = 3
    
    # Symbol limits
    max_positions_per_symbol: int = 2
    max_total_positions: int = 10
    
    # Spread and volatility filters
    max_spread_points: float = 3.0  # Maximum spread in points
    min_volatility_atr: float = 0.0  # Minimum ATR (0 = disabled)
    max_volatility_atr: float = 1000.0  # Maximum ATR
    
    # Correlation limits
    max_correlation_exposure: float = 0.7  # Max correlated position exposure
    
    # Kill switch
    kill_switch_active: bool = False
    
    def __post_init__(self):
        """Load from environment if available"""
        self.daily_loss_limit_pct = float(os.getenv('RISK_DAILY_LOSS_LIMIT_PCT', self.daily_loss_limit_pct))
        self.max_consecutive_losses = int(os.getenv('RISK_CONSECUTIVE_LOSS_LIMIT', self.max_consecutive_losses))
        self.max_position_size_pct = float(os.getenv('RISK_MAX_POSITION_SIZE_PCT', self.max_position_size_pct))
        self.max_total_exposure_pct = float(os.getenv('RISK_MAX_TOTAL_EXPOSURE_PCT', self.max_total_exposure_pct))


@dataclass
class RiskAssessment:
    """Risk assessment result"""
    approved: bool
    risk_level: RiskLevel
    position_size_lots: float
    reasons: List[str]
    warnings: List[str]
    metrics: Dict


class RiskManager:
    """Risk Management Engine"""
    
    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or RiskConfig()
        self.daily_stats = {
            "pnl": 0.0,
            "trades_count": 0,
            "consecutive_losses": 0,
            "last_reset": datetime.utcnow().date()
        }
    
    def assess_trade(
        self,
        symbol: str,
        direction: str,
        account_balance: float,
        account_equity: float,
        signal_confidence: float,
        stop_loss_points: float,
        current_positions: List[Dict],
        spread_points: Optional[float] = None,
        volatility_atr: Optional[float] = None
    ) -> RiskAssessment:
        """
        Comprehensive risk assessment for a trade
        
        Args:
            symbol: Trading symbol
            direction: buy or sell
            account_balance: Account balance
            account_equity: Account equity
            signal_confidence: AI model confidence (0-1)
            stop_loss_points: Distance to stop loss in points
            current_positions: List of currently open positions
            spread_points: Current spread in points
            volatility_atr: Current ATR value
            
        Returns:
            RiskAssessment with approval decision
        """
        reasons = []
        warnings = []
        approved = True
        risk_level = RiskLevel.LOW
        
        # Reset daily stats if new day
        self._check_daily_reset()
        
        # 1. Kill Switch Check
        if self.config.kill_switch_active:
            approved = False
            reasons.append("Kill switch is active")
            return RiskAssessment(
                approved=False,
                risk_level=RiskLevel.CRITICAL,
                position_size_lots=0.0,
                reasons=reasons,
                warnings=warnings,
                metrics={}
            )
        
        # 2. Daily Loss Limit Check
        daily_loss_limit = account_equity * (self.config.daily_loss_limit_pct / 100)
        if self.daily_stats["pnl"] <= -daily_loss_limit:
            approved = False
            reasons.append(f"Daily loss limit reached: ${abs(self.daily_stats['pnl']):.2f} / ${daily_loss_limit:.2f}")
            risk_level = RiskLevel.CRITICAL
        
        # 3. Consecutive Losses Check
        if self.daily_stats["consecutive_losses"] >= self.config.max_consecutive_losses:
            approved = False
            reasons.append(f"Consecutive loss limit reached: {self.daily_stats['consecutive_losses']}")
            risk_level = RiskLevel.CRITICAL
        elif self.daily_stats["consecutive_losses"] >= self.config.max_consecutive_losses - 1:
            warnings.append(f"Warning: {self.daily_stats['consecutive_losses']} consecutive losses")
            risk_level = RiskLevel.HIGH
        
        # 4. Total Positions Limit
        if len(current_positions) >= self.config.max_total_positions:
            approved = False
            reasons.append(f"Maximum total positions reached: {len(current_positions)}")
        
        # 5. Symbol Position Limit
        symbol_positions = [p for p in current_positions if p.get('symbol') == symbol]
        if len(symbol_positions) >= self.config.max_positions_per_symbol:
            approved = False
            reasons.append(f"Maximum positions for {symbol} reached: {len(symbol_positions)}")
        
        # 6. Spread Filter
        if spread_points is not None and spread_points > self.config.max_spread_points:
            approved = False
            reasons.append(f"Spread too wide: {spread_points:.1f} points > {self.config.max_spread_points}")
        
        # 7. Volatility Filter
        if volatility_atr is not None:
            if volatility_atr < self.config.min_volatility_atr:
                approved = False
                reasons.append(f"Volatility too low: ATR {volatility_atr:.4f} < {self.config.min_volatility_atr}")
            elif volatility_atr > self.config.max_volatility_atr:
                approved = False
                reasons.append(f"Volatility too high: ATR {volatility_atr:.4f} > {self.config.max_volatility_atr}")
        
        # 8. Calculate Position Size
        position_size_lots = self._calculate_position_size(
            account_equity,
            signal_confidence,
            stop_loss_points
        )
        
        # 9. Check Total Exposure
        current_exposure = sum(p.get('volume', 0) * 100000 for p in current_positions)  # Assume 1 lot = 100k
        new_exposure = current_exposure + (position_size_lots * 100000)
        max_exposure = account_equity * (self.config.max_total_exposure_pct / 100)
        
        if new_exposure > max_exposure:
            # Reduce position size
            max_new_lots = (max_exposure - current_exposure) / 100000
            if max_new_lots <= 0:
                approved = False
                reasons.append(f"Total exposure limit reached: ${current_exposure:.2f} / ${max_exposure:.2f}")
            else:
                position_size_lots = min(position_size_lots, max_new_lots)
                warnings.append(f"Position size reduced due to exposure limit: {position_size_lots:.2f} lots")
                risk_level = RiskLevel.MEDIUM
        
        # 10. Signal Confidence Check
        if signal_confidence < 0.6:
            warnings.append(f"Low signal confidence: {signal_confidence:.2%}")
            risk_level = max(risk_level, RiskLevel.MEDIUM, key=lambda x: list(RiskLevel).index(x))
        elif signal_confidence < 0.5:
            approved = False
            reasons.append(f"Signal confidence too low: {signal_confidence:.2%}")
        
        # Compile metrics
        metrics = {
            "daily_pnl": self.daily_stats["pnl"],
            "daily_trades": self.daily_stats["trades_count"],
            "consecutive_losses": self.daily_stats["consecutive_losses"],
            "current_positions": len(current_positions),
            "current_exposure": current_exposure,
            "max_exposure": max_exposure,
            "exposure_utilization_pct": (current_exposure / max_exposure * 100) if max_exposure > 0 else 0,
            "position_size_lots": position_size_lots,
            "signal_confidence": signal_confidence,
            "spread_points": spread_points,
            "volatility_atr": volatility_atr
        }
        
        return RiskAssessment(
            approved=approved,
            risk_level=risk_level,
            position_size_lots=position_size_lots,
            reasons=reasons,
            warnings=warnings,
            metrics=metrics
        )
    
    def _calculate_position_size(
        self,
        account_equity: float,
        signal_confidence: float,
        stop_loss_points: float
    ) -> float:
        """
        Calculate position size using Kelly Criterion + confidence adjustment
        
        Args:
            account_equity: Account equity
            signal_confidence: Model confidence
            stop_loss_points: SL distance in points
            
        Returns:
            Position size in lots
        """
        # Base risk per trade (% of equity)
        base_risk_pct = self.config.max_position_size_pct
        
        # Adjust risk based on confidence (0.5-1.0 confidence -> 50-100% of base risk)
        confidence_multiplier = max(0.5, signal_confidence)
        risk_pct = base_risk_pct * confidence_multiplier
        
        # Calculate risk amount
        risk_amount = account_equity * (risk_pct / 100)
        
        # Calculate lots (simplified - assumes 1 pip = $10 for standard lot)
        # In production, this should use actual pip value from MT5
        point_value = 10  # $10 per pip for 1 standard lot
        
        if stop_loss_points == 0:
            stop_loss_points = 50  # Default SL if not provided
        
        lots = risk_amount / (stop_loss_points * point_value)
        
        # Round to 0.01 (minimum lot step)
        lots = round(lots, 2)
        
        # Clamp to reasonable range
        lots = max(0.01, min(lots, 10.0))
        
        return lots
    
    def update_daily_stats(self, trade_result: Dict):
        """
        Update daily statistics after trade closes
        
        Args:
            trade_result: Dictionary with trade results (pnl, win/loss, etc.)
        """
        self._check_daily_reset()
        
        pnl = trade_result.get('net_pnl', 0)
        self.daily_stats["pnl"] += pnl
        self.daily_stats["trades_count"] += 1
        
        # Update consecutive losses
        if pnl < 0:
            self.daily_stats["consecutive_losses"] += 1
        else:
            self.daily_stats["consecutive_losses"] = 0
    
    def _check_daily_reset(self):
        """Reset daily stats if new day"""
        today = datetime.utcnow().date()
        if self.daily_stats["last_reset"] < today:
            self.daily_stats = {
                "pnl": 0.0,
                "trades_count": 0,
                "consecutive_losses": 0,
                "last_reset": today
            }
    
    def activate_kill_switch(self, reason: str = "Manual activation"):
        """Activate kill switch to stop all trading"""
        self.config.kill_switch_active = True
        print(f"🚨 KILL SWITCH ACTIVATED: {reason}")
    
    def deactivate_kill_switch(self):
        """Deactivate kill switch"""
        self.config.kill_switch_active = False
        print(f"✅ Kill switch deactivated")
    
    def get_risk_metrics(self) -> Dict:
        """Get current risk metrics"""
        return {
            "kill_switch_active": self.config.kill_switch_active,
            "daily_pnl": self.daily_stats["pnl"],
            "daily_trades": self.daily_stats["trades_count"],
            "consecutive_losses": self.daily_stats["consecutive_losses"],
            "daily_loss_limit": self.config.daily_loss_limit_pct,
            "max_consecutive_losses": self.config.max_consecutive_losses,
            "last_reset": self.daily_stats["last_reset"].isoformat()
        }


# Global risk manager instance
risk_manager = RiskManager()
