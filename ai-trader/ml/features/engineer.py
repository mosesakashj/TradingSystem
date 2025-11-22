# Feature Engineering Pipeline for Trading Signals
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas_ta as ta


class FeatureEngineer:
    """Feature engineering for trading ML models"""
    
    def __init__(self):
        self.feature_names = []
    
    def engineer_features(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str = '1h'
    ) -> pd.DataFrame:
        """
        Create comprehensive feature set from OHLCV data
        
        Args:
            df: DataFrame with OHLCV columns (open, high, low, close, volume)
            symbol: Trading symbol
            timeframe: Chart timeframe
            
        Returns:
            DataFrame with engineered features
        """
        df = df.copy()
        
        # Ensure we have required columns
        required = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required):
            raise ValueError(f"DataFrame must have columns: {required}")
        
        # 1. Price-based features
        df = self._add_price_features(df)
        
        # 2. Technical indicators
        df = self._add_technical_indicators(df)
        
        # 3. Volume features
        df = self._add_volume_features(df)
        
        # 4. Volatility features
        df = self._add_volatility_features(df)
        
        # 5. Time-based features
        df = self._add_time_features(df, timeframe)
        
        # 6. Market regime features
        df = self._add_regime_features(df)
        
        # 7. Pattern recognition
        df = self._add_pattern_features(df)
        
        # Drop NaN rows (from indicator calculation)
        df = df.dropna()
        
        # Store feature names
        self.feature_names = [col for col in df.columns if col not in required + ['timestamp']]
        
        return df
    
    def _add_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add price-based features"""
        # Returns
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # Price ratios
        df['high_low_ratio'] = df['high'] / df['low']
        df['close_open_ratio'] = df['close'] / df['open']
        
        # Price position in range
        df['price_position'] = (df['close'] - df['low']) / (df['high'] - df['low'])
        
        # Gap
        df['gap'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
        
        return df
    
    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators using pandas-ta"""
        # Moving averages
        df['sma_10'] = ta.sma(df['close'], length=10)
        df['sma_20'] = ta.sma(df['close'], length=20)
        df['sma_50'] = ta.sma(df['close'], length=50)
        df['ema_10'] = ta.ema(df['close'], length=10)
        df['ema_20'] = ta.ema(df['close'], length=20)
        
        # MA crossovers
        df['sma_10_20_cross'] = (df['sma_10'] > df['sma_20']).astype(int)
        df['price_above_sma_50'] = (df['close'] > df['sma_50']).astype(int)
        
        # RSI
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['rsi_oversold'] = (df['rsi'] < 30).astype(int)
        df['rsi_overbought'] = (df['rsi'] > 70).astype(int)
        
        # MACD
        macd = ta.macd(df['close'])
        if macd is not None and not macd.empty:
            df['macd'] = macd['MACD_12_26_9']
            df['macd_signal'] = macd['MACDs_12_26_9']
            df['macd_hist'] = macd['MACDh_12_26_9']
            df['macd_cross'] = (df['macd'] > df['macd_signal']).astype(int)
        
        # Bollinger Bands
        bbands = ta.bbands(df['close'], length=20)
        if bbands is not None and not bbands.empty:
            df['bb_upper'] = bbands['BBU_20_2.0']
            df['bb_middle'] = bbands['BBM_20_2.0']
            df['bb_lower'] = bbands['BBL_20_2.0']
            df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
            df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # ATR (Average True Range)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        df['atr_pct'] = df['atr'] / df['close']
        
        # ADX (Trend Strength)
        adx = ta.adx(df['high'], df['low'], df['close'], length=14)
        if adx is not None and not adx.empty:
            df['adx'] = adx['ADX_14']
            df['di_plus'] = adx['DMP_14']
            df['di_minus'] = adx['DMN_14']
        
        # Stochastic
        stoch = ta.stoch(df['high'], df['low'], df['close'])
        if stoch is not None and not stoch.empty:
            df['stoch_k'] = stoch['STOCHk_14_3_3']
            df['stoch_d'] = stoch['STOCHd_14_3_3']
        
        return df
    
    def _add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volume-based features"""
        # Volume moving averages
        df['volume_sma_10'] = ta.sma(df['volume'], length=10)
        df['volume_sma_20'] = ta.sma(df['volume'], length=20)
        
        # Volume ratio
        df['volume_ratio'] = df['volume'] / df['volume_sma_20']
        
        # High volume flag
        df['high_volume'] = (df['volume'] > df['volume_sma_20'] * 1.5).astype(int)
        
        # OBV (On-Balance Volume)
        df['obv'] = ta.obv(df['close'], df['volume'])
        
        return df
    
    def _add_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volatility features"""
        # Historical volatility
        df['volatility_10'] = df['returns'].rolling(10).std()
        df['volatility_20'] = df['returns'].rolling(20).std()
        
        # True range
        df['true_range'] = ta.true_range(df['high'], df['low'], df['close'])
        
        return df
    
    def _add_time_features(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """Add time-based features"""
        if 'timestamp' in df.columns:
            df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
            df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.dayofweek
            df['day_of_month'] = pd.to_datetime(df['timestamp']).dt.day
            
            # Trading session (simplified - assumes UTC)
            # Asian: 0-9, London: 9-17, NY: 14-22
            df['asian_session'] = ((df['hour'] >= 0) & (df['hour'] < 9)).astype(int)
            df['london_session'] = ((df['hour'] >= 9) & (df['hour'] < 17)).astype(int)
            df['ny_session'] = ((df['hour'] >= 14) & (df['hour'] < 22)).astype(int)
        
        return df
    
    def _add_regime_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add market regime features"""
        # Trend strength (ADX-based if available)
        if 'adx' in df.columns:
            df['strong_trend'] = (df['adx'] > 25).astype(int)
            df['weak_trend'] = (df['adx'] < 20).astype(int)
        
        # Trend direction (using SMAs)
        if 'sma_10' in df.columns and 'sma_50' in df.columns:
            df['uptrend'] = (df['sma_10'] > df['sma_50']).astype(int)
            df['downtrend'] = (df['sma_10'] < df['sma_50']).astype(int)
        
        # Ranging market (using Bollinger Bands)
        if 'bb_width' in df.columns:
            df['ranging_market'] = (df['bb_width'] < df['bb_width'].rolling(20).mean() * 0.8).astype(int)
        
        return df
    
    def _add_pattern_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add candlestick pattern features"""
        # Doji
        body = abs(df['close'] - df['open'])
        total_range = df['high'] - df['low']
        df['doji'] = (body / total_range < 0.1).astype(int)
        
        # Hammer / Hanging Man
        lower_shadow = df[['open', 'close']].min(axis=1) - df['low']
        upper_shadow = df['high'] - df[['open', 'close']].max(axis=1)
        df['hammer'] = ((lower_shadow > body * 2) & (upper_shadow < body)).astype(int)
        
        # Engulfing patterns
        df['bullish_engulfing'] = (
            (df['close'] > df['open']) &
            (df['close'].shift(1) < df['open'].shift(1)) &
            (df['open'] < df['close'].shift(1)) &
            (df['close'] > df['open'].shift(1))
        ).astype(int)
        
        df['bearish_engulfing'] = (
            (df['close'] < df['open']) &
            (df['close'].shift(1) > df['open'].shift(1)) &
            (df['open'] > df['close'].shift(1)) &
            (df['close'] < df['open'].shift(1))
        ).astype(int)
        
        return df
    
    def get_feature_importance(self, model, top_n: int = 20) -> pd.DataFrame:
        """Get feature importance from trained model"""
        if hasattr(model, 'feature_importances_'):
            # Tree-based models (LightGBM, XGBoost)
            importance = pd.DataFrame({
                'feature': self.feature_names,
                'importance': model.feature_importances_
            })
            return importance.sort_values('importance', ascending=False).head(top_n)
        else:
            return pd.DataFrame()
    
    def normalize_features(self, df: pd.DataFrame, method: str = 'zscore') -> pd.DataFrame:
        """Normalize features for neural networks"""
        df = df.copy()
        
        feature_cols = [col for col in df.columns if col not in ['open', 'high', 'low', 'close', 'volume', 'timestamp']]
        
        if method == 'zscore':
            # Z-score normalization
            df[feature_cols] = (df[feature_cols] - df[feature_cols].mean()) / df[feature_cols].std()
        elif method == 'minmax':
            # Min-max normalization
            df[feature_cols] = (df[feature_cols] - df[feature_cols].min()) / (df[feature_cols].max() - df[feature_cols].min())
        
        return df


# Global feature engineer instance
feature_engineer = FeatureEngineer()
