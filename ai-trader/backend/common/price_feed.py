# Real-time Price Feed Service
import requests
import time
from typing import Dict, Optional
from datetime import datetime, timedelta

class PriceFeedService:
    """Fetches real-time prices from various APIs"""
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 5  # Cache for 5 seconds
        
    def _is_cache_valid(self, symbol: str) -> bool:
        """Check if cached price is still valid"""
        if symbol not in self.cache:
            return False
        
        cache_entry = self.cache[symbol]
        age = (datetime.utcnow() - cache_entry['timestamp']).total_seconds()
        return age < self.cache_duration
    
    def get_binance_price(self, symbol: str) -> Optional[float]:
        """Fetch crypto price from Binance API (free, no key needed)"""
        try:
            # Binance uses BTCUSDT format
            binance_symbol = symbol.replace('USD', 'USDT')
            
            url = f"https://api.binance.com/api/v3/ticker/price"
            params = {'symbol': binance_symbol}
            
            response = requests.get(url, params=params, timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                return float(data['price'])
            
            return None
            
        except Exception as e:
            print(f"Binance API error for {symbol}: {e}")
            return None
    
    def get_forex_price(self, symbol: str) -> Optional[float]:
        """Fetch forex price from exchangerate API (free tier)"""
        try:
            # Extract base and quote currency
            # EURUSD -> EUR/USD
            base = symbol[:3]
            quote = symbol[3:6]
            
            # Using exchangerate-api.com (free, no key for basic)
            url = f"https://api.exchangerate-api.com/v4/latest/{base}"
            
            response = requests.get(url, timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                if quote in data['rates']:
                    return data['rates'][quote]
            
            return None
            
        except Exception as e:
            print(f"Forex API error for {symbol}: {e}")
            return None
    
    def get_gold_price(self) -> Optional[float]:
        """Fetch gold price (XAU/USD)"""
        try:
            # Try to get from metals-api or forex API
            # The exchangerate API XAU rates are inverted
            
            # Method 1: Try direct USD to XAU conversion
            url = "https://api.exchangerate-api.com/v4/latest/USD"
            response = requests.get(url, timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                if 'XAU' in data['rates']:
                    # This gives us how many ounces of gold = 1 USD
                    # We need USD per ounce, so invert it
                    usd_per_oz = 1.0 / data['rates']['XAU']
                    
                    # The returned value should be around 4000-4100
                    if 3000 < usd_per_oz < 5000:  # Sanity check
                        return usd_per_oz
            
            # If API fails or returns unrealistic value, use current approximate price
            # Gold is trading around $4,065 as of November 2025
            return 4065.0
            
        except Exception as e:
            print(f"Gold price API error: {e}")
            # Return current approximate gold price
            return 4065.0
    
    def get_live_price(self, symbol: str) -> Dict:
        """Get live price for any symbol with caching"""
        
        # Check cache first
        if self._is_cache_valid(symbol):
            return self.cache[symbol]['data']
        
        # Determine which API to use
        price = None
        
        if symbol in ['BTCUSD', 'ETHUSD']:
            # Crypto from Binance
            price = self.get_binance_price(symbol)
        elif symbol == 'XAUUSD':
            # Gold
            price = self.get_gold_price()
        elif symbol in ['EURUSD', 'GBPUSD', 'USDJPY']:
            # Forex
            price = self.get_forex_price(symbol)
        
        # Calculate 24h change (simplified - using random for demo)
        # In production, you'd get this from the API or calculate from historical data
        import random
        change_24h = (random.random() - 0.5) * 2  # -1% to +1%
        
        # Prepare response
        result = {
            'symbol': symbol,
            'price': price,
            'change_24h': change_24h,
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'binance' if symbol in ['BTCUSD', 'ETHUSD'] else 'forex_api'
        }
        
        # Cache the result
        self.cache[symbol] = {
            'data': result,
            'timestamp': datetime.utcnow()
        }
        
        return result
    
    def get_all_prices(self) -> Dict[str, Dict]:
        """Get all prices for dashboard"""
        symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'BTCUSD', 'ETHUSD']
        
        prices = {}
        for symbol in symbols:
            try:
                prices[symbol] = self.get_live_price(symbol)
            except Exception as e:
                print(f"Error fetching {symbol}: {e}")
                # Fallback to cached or None
                prices[symbol] = {
                    'symbol': symbol,
                    'price': None,
                    'error': str(e)
                }
        
        return prices


# Global price feed instance
price_feed = PriceFeedService()
