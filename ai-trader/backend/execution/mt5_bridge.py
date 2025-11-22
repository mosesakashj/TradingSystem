# MT5 Execution Engine - Broker Integration
import MetaTrader5 as mt5
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import time
import os


class MT5OrderType(Enum):
    """MT5 order types"""
    BUY = mt5.ORDER_TYPE_BUY
    SELL = mt5.ORDER_TYPE_SELL
    BUY_LIMIT = mt5.ORDER_TYPE_BUY_LIMIT
    SELL_LIMIT = mt5.ORDER_TYPE_SELL_LIMIT
    BUY_STOP = mt5.ORDER_TYPE_BUY_STOP
    SELL_STOP = mt5.ORDER_TYPE_SELL_STOP


@dataclass
class OrderRequest:
    """Order request parameters"""
    symbol: str
    order_type: str  # 'buy' or 'sell'
    lots: float
    entry_price: Optional[float] = None  # For market orders, ignored
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    deviation: int = 20  # Max price deviation in points
    magic: int = 234000  # Magic number for identification
    comment: str = "AI Trading Bot"


@dataclass
class OrderResult:
    """Order execution result"""
    success: bool
    order_ticket: Optional[int] = None
    position_id: Optional[int] = None
    filled_price: Optional[float] = None
    filled_lots: Optional[float] = None
    slippage_points: Optional[float] = None
    commission: Optional[float] = None
    error_code: Optional[int] = None
    error_message: Optional[str] = None
    latency_ms: Optional[float] = None


class MT5ExecutionEngine:
    """MetaTrader 5 Execution Engine"""
    
    def __init__(self):
        self.connected = False
        self.account_info = None
    
    def connect(
        self,
        login: Optional[str] = None,
        password: Optional[str] = None,
        server: Optional[str] = None
    ) -> bool:
        """
        Connect to MT5 terminal
        
        Args:
            login: MT5 account login
            password: MT5 password
            server: Broker server name
            
        Returns:
            True if connected successfully
        """
        # Get credentials from env if not provided
        login = login or os.getenv('MT5_LOGIN')
        password = password or os.getenv('MT5_PASSWORD')
        server = server or os.getenv('MT5_SERVER')
        
        if not all([login, password, server]):
            print("❌ MT5 credentials not provided")
            return False
        
        # Initialize MT5
        if not mt5.initialize():
            print(f"❌ MT5 initialization failed: {mt5.last_error()}")
            return False
        
        # Login to account
        authorized = mt5.login(int(login), password=password, server=server)
        
        if not authorized:
            error = mt5.last_error()
            print(f"❌ MT5 login failed: {error}")
            mt5.shutdown()
            return False
        
        self.connected = True
        self.account_info = mt5.account_info()
        
        print(f"✅ MT5 connected")
        print(f"   Account: {self.account_info.login}")
        print(f"   Server: {self.account_info.server}")
        print(f"   Balance: ${self.account_info.balance:.2f}")
        print(f"   Equity: ${self.account_info.equity:.2f}")
        
        return True
    
    def disconnect(self):
        """Disconnect from MT5"""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            print("✅ MT5 disconnected")
    
    def is_connected(self) -> bool:
        """Check if MT5 is connected"""
        return self.connected and mt5.terminal_info() is not None
    
    def get_account_info(self) -> Dict:
        """Get current account information"""
        if not self.is_connected():
            return {"error": "Not connected"}
        
        account = mt5.account_info()
        if account is None:
            return {"error": "Failed to get account info"}
        
        return {
            "login": account.login,
            "server": account.server,
            "balance": account.balance,
            "equity": account.equity,
            "margin": account.margin,
            "margin_free": account.margin_free,
            "margin_level": account.margin_level,
            "profit": account.profit,
            "currency": account.currency
        }
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get symbol trading information"""
        if not self.is_connected():
            return None
        
        info = mt5.symbol_info(symbol)
        if info is None:
            return None
        
        return {
            "symbol": info.name,
            "bid": info.bid,
            "ask": info.ask,
            "spread": info.spread,
            "spread_points": (info.ask - info.bid) / info.point,
            "point": info.point,
            "digits": info.digits,
            "trade_contract_size": info.trade_contract_size,
            "volume_min": info.volume_min,
            "volume_max": info.volume_max,
            "volume_step": info.volume_step,
        }
    
    def calculate_lot_size(
        self,
        symbol: str,
        risk_amount: float,
        stop_loss_points: float
    ) -> float:
        """
        Calculate lot size based on risk amount and SL distance
        
        Args:
            symbol: Trading symbol
            risk_amount: Dollar amount to risk
            stop_loss_points: Distance to SL in points
            
        Returns:
            Calculated lot size
        """
        symbol_info = self.get_symbol_info(symbol)
        if not symbol_info:
            return 0.01  # Minimum lot
        
        # Calculate value per lot per point
        point_value = symbol_info['trade_contract_size'] * symbol_info['point']
        
        # Calculate lots
        lots = risk_amount / (stop_loss_points * point_value)
        
        # Round to volume step
        volume_step = symbol_info['volume_step']
        lots = round(lots / volume_step) * volume_step
        
        # Clamp to min/max
        lots = max(symbol_info['volume_min'], min(lots, symbol_info['volume_max']))
        
        return lots
    
    def place_market_order(self, order_req: OrderRequest) -> OrderResult:
        """
        Place market order
        
        Args:
            order_req: Order request parameters
            
        Returns:
            OrderResult with execution details
        """
        start_time = time.time()
        
        if not self.is_connected():
            return OrderResult(
                success=False,
                error_message="MT5 not connected"
            )
        
        # Get symbol info
        symbol_info = self.get_symbol_info(order_req.symbol)
        if not symbol_info:
            return OrderResult(
                success=False,
                error_message=f"Symbol {order_req.symbol} not found"
            )
        
        # Determine order type
        if order_req.order_type.lower() == 'buy':
            order_type = mt5.ORDER_TYPE_BUY
            price = symbol_info['ask']
        else:
            order_type = mt5.ORDER_TYPE_SELL
            price = symbol_info['bid']
        
        # Prepare request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": order_req.symbol,
            "volume": order_req.lots,
            "type": order_type,
            "price": price,
            "deviation": order_req.deviation,
            "magic": order_req.magic,
            "comment": order_req.comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,  # Immediate or Cancel
        }
        
        # Add SL/TP if provided
        if order_req.stop_loss:
            request["sl"] = order_req.stop_loss
        if order_req.take_profit:
            request["tp"] = order_req.take_profit
        
        # Send order
        result = mt5.order_send(request)
        
        latency_ms = (time.time() - start_time) * 1000
        
        if result is None:
            return OrderResult(
                success=False,
                error_message="Order send failed - no result",
                latency_ms=latency_ms
            )
        
        # Check result
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return OrderResult(
                success=False,
                error_code=result.retcode,
                error_message=f"Order failed: {result.comment}",
                latency_ms=latency_ms
            )
        
        # Calculate slippage
        slippage_points = abs(result.price - price) / symbol_info['point']
        
        return OrderResult(
            success=True,
            order_ticket=result.order,
            position_id=result.deal if hasattr(result, 'deal') else result.order,
            filled_price=result.price,
            filled_lots=result.volume,
            slippage_points=slippage_points,
            latency_ms=latency_ms
        )
    
    def close_position(self, position_id: int) -> OrderResult:
        """
        Close an open position
        
        Args:
            position_id: MT5 position ID
            
        Returns:
            OrderResult with close details
        """
        start_time = time.time()
        
        if not self.is_connected():
            return OrderResult(
                success=False,
                error_message="MT5 not connected"
            )
        
        # Get position info
        positions = mt5.positions_get(ticket=position_id)
        
        if not positions or len(positions) == 0:
            return OrderResult(
                success=False,
                error_message=f"Position {position_id} not found"
            )
        
        position = positions[0]
        
        # Determine close order type (opposite of position)
        if position.type == mt5.ORDER_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(position.symbol).bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(position.symbol).ask
        
        # Prepare close request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": order_type,
            "position": position_id,
            "price": price,
            "deviation": 20,
            "magic": position.magic,
            "comment": "close position",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # Send close order
        result = mt5.order_send(request)
        
        latency_ms = (time.time() - start_time) * 1000
        
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            return OrderResult(
                success=False,
                error_code=result.retcode if result else None,
                error_message=f"Close failed: {result.comment if result else 'unknown'}",
                latency_ms=latency_ms
            )
        
        return OrderResult(
            success=True,
            order_ticket=result.order,
            filled_price=result.price,
            filled_lots=result.volume,
            latency_ms=latency_ms
        )
    
    def get_open_positions(self) -> list:
        """Get all open positions"""
        if not self.is_connected():
            return []
        
        positions = mt5.positions_get()
        if positions is None:
            return []
        
        return [
            {
                "ticket": pos.ticket,
                "symbol": pos.symbol,
                "type": "buy" if pos.type == mt5.ORDER_TYPE_BUY else "sell",
                "volume": pos.volume,
                "price_open": pos.price_open,
                "price_current": pos.price_current,
                "sl": pos.sl,
                "tp": pos.tp,
                "profit": pos.profit,
                "swap": pos.swap,
                "comment": pos.comment,
                "time": datetime.fromtimestamp(pos.time)
            }
            for pos in positions
        ]
    
    def modify_position(
        self,
        position_id: int,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> OrderResult:
        """Modify SL/TP of an open position"""
        start_time = time.time()
        
        if not self.is_connected():
            return OrderResult(success=False, error_message="MT5 not connected")
        
        positions = mt5.positions_get(ticket=position_id)
        if not positions:
            return OrderResult(success=False, error_message=f"Position {position_id} not found")
        
        position = positions[0]
        
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": position.symbol,
            "position": position_id,
            "sl": stop_loss if stop_loss is not None else position.sl,
            "tp": take_profit if take_profit is not None else position.tp,
        }
        
        result = mt5.order_send(request)
        latency_ms = (time.time() - start_time) * 1000
        
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            return OrderResult(
                success=False,
                error_code=result.retcode if result else None,
                error_message=f"Modify failed: {result.comment if result else 'unknown'}",
                latency_ms=latency_ms
            )
        
        return OrderResult(success=True, latency_ms=latency_ms)


# Global MT5 engine instance
mt5_engine = MT5ExecutionEngine()
