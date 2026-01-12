"""
Strategy Super Patron Module
Binary Option Trading Entry Points Calculator using:
- Bollinger Bands (period=6, deviation=2)
- EMA 100
- CCI (period=14)
- Stochastic Oscillator (K=13, smoothing=3, D=3)
"""

import logging
import threading
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import numpy as np
import talib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StrategyIndicators:
    """Calculate technical indicators for the strategy"""
    
    @staticmethod
    def calculate_bollinger_bands(close_prices: pd.Series, period: int = 6, deviation: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate Bollinger Bands
        
        Args:
            close_prices: Series of closing prices
            period: Period for moving average (default: 6)
            deviation: Standard deviation multiplier (default: 2.0)
            
        Returns:
            Tuple of (upper_band, middle_band, lower_band)
        """
        upper, middle, lower = talib.BBANDS(
            close_prices.values,
            timeperiod=period,
            nbdevup=deviation,
            nbdevdn=deviation,
            matype=0
        )
        return pd.Series(upper), pd.Series(middle), pd.Series(lower)
    
    @staticmethod
    def calculate_ema(close_prices: pd.Series, period: int = 100) -> pd.Series:
        """
        Calculate Exponential Moving Average
        
        Args:
            close_prices: Series of closing prices
            period: Period for EMA (default: 100)
            
        Returns:
            EMA values as Series
        """
        ema = talib.EMA(close_prices.values, timeperiod=period)
        return pd.Series(ema)
    
    @staticmethod
    def calculate_cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Commodity Channel Index
        
        Args:
            high: Series of high prices
            low: Series of low prices
            close: Series of closing prices
            period: Period for CCI (default: 14)
            
        Returns:
            CCI values as Series
        """
        cci = talib.CCI(high.values, low.values, close.values, timeperiod=period)
        return pd.Series(cci)
    
    @staticmethod
    def calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series, 
                            fastk_period: int = 13, slowk_period: int = 3, 
                            slowd_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate Stochastic Oscillator
        
        Args:
            high: Series of high prices
            low: Series of low prices
            close: Series of closing prices
            fastk_period: Period for fast K (default: 13)
            slowk_period: Smoothing period for slow K (default: 3)
            slowd_period: Period for slow D (default: 3)
            
        Returns:
            Tuple of (slowk, slowd)
        """
        slowk, slowd = talib.STOCH(
            high.values, 
            low.values, 
            close.values,
            fastk_period=fastk_period,
            slowk_period=slowk_period,
            slowk_matype=0,
            slowd_period=slowd_period,
            slowd_matype=0
        )
        return pd.Series(slowk), pd.Series(slowd)


class SignalGenerator:
    """Generate trading signals based on indicators"""
    
    @staticmethod
    def check_bollinger_signal(close_prices: pd.Series, bb_upper: pd.Series, bb_lower: pd.Series) -> Optional[str]:
        """
        Check Bollinger Bands signal
        
        Args:
            close_prices: Series of closing prices
            bb_upper: Upper Bollinger Band
            bb_lower: Lower Bollinger Band
            
        Returns:
            'call' if price crosses below lower band, 'put' if price crosses above upper band, None otherwise
        """
        if len(close_prices) < 2 or pd.isna(bb_lower.iloc[-1]) or pd.isna(bb_upper.iloc[-1]):
            return None
        
        # Call signal: Candle crosses below lower band
        if close_prices.iloc[-1] < bb_lower.iloc[-1]:
            return 'call'
        
        # Put signal: Candle crosses above upper band
        if close_prices.iloc[-1] > bb_upper.iloc[-1]:
            return 'put'
        
        return None
    
    @staticmethod
    def check_ema_signal(close_price: float, ema_value: float) -> Optional[str]:
        """
        Check EMA signal
        
        Args:
            close_price: Current closing price
            ema_value: Current EMA value
            
        Returns:
            'call' if EMA is below price, 'put' if EMA is above price, None if invalid
        """
        if pd.isna(ema_value):
            return None
        
        # Call signal: EMA is below the candle price
        if ema_value < close_price:
            return 'call'
        
        # Put signal: EMA is above the candle price
        if ema_value > close_price:
            return 'put'
        
        return None
    
    @staticmethod
    def check_cci_signal(cci_value: float) -> Optional[str]:
        """
        Check CCI signal
        
        Args:
            cci_value: Current CCI value
            
        Returns:
            'call' if CCI < -100 (oversold), 'put' if CCI > 100 (overbought), None otherwise
        """
        if pd.isna(cci_value):
            return None
        
        # Call signal: Value is below -100 (oversold)
        if cci_value < -100:
            return 'call'
        
        # Put signal: Value is above 100 (overbought)
        if cci_value > 100:
            return 'put'
        
        return None
    
    @staticmethod
    def check_stochastic_signal(stoch_k: float, stoch_oversold: float = 20, stoch_overbought: float = 80) -> Optional[str]:
        """
        Check Stochastic Oscillator signal
        
        Args:
            stoch_k: Current Stochastic K value
            stoch_oversold: Oversold threshold (default: 20)
            stoch_overbought: Overbought threshold (default: 80)
            
        Returns:
            'call' if Stochastic < 20 (oversold), 'put' if Stochastic > 80 (overbought), None otherwise
        """
        if pd.isna(stoch_k):
            return None
        
        # Call signal: Value is below 20 (oversold)
        if stoch_k < stoch_oversold:
            return 'call'
        
        # Put signal: Value is above 80 (overbought)
        if stoch_k > stoch_overbought:
            return 'put'
        
        return None


class StrategyEngine:
    """Main strategy engine for processing actives and generating signals"""
    
    def __init__(self, max_workers: int = 5):
        """
        Initialize Strategy Engine
        
        Args:
            max_workers: Maximum number of threads for parallel processing
        """
        self.max_workers = max_workers
        self.indicators = StrategyIndicators()
        self.signal_generator = SignalGenerator()
        self.lock = threading.Lock()
    
    def process_active(self, active: str, candle_data: pd.DataFrame) -> Dict[str, any]:
        """
        Process a single active and generate trading signal
        
        Args:
            active: Active name (e.g., 'EURUSD', 'USDJPY')
            candle_data: DataFrame with columns ['open', 'high', 'low', 'close', 'volume']
            
        Returns:
            Dictionary with active name, action, and indicator values
        """
        try:
            logger.info(f"Processing active: {active}")
            
            # Validate input data
            if candle_data is None or len(candle_data) < 100:
                logger.warning(f"Insufficient data for {active}: {len(candle_data) if candle_data is not None else 0} candles")
                return {'active': active, 'action': None, 'error': 'Insufficient data'}
            
            # Extract price data
            high = candle_data['high']
            low = candle_data['low']
            close = candle_data['close']
            
            # Calculate indicators
            bb_upper, bb_middle, bb_lower = self.indicators.calculate_bollinger_bands(close)
            ema = self.indicators.calculate_ema(close)
            cci = self.indicators.calculate_cci(high, low, close)
            stoch_k, stoch_d = self.indicators.calculate_stochastic(high, low, close)
            
            # Get current values (last valid value)
            current_close = close.iloc[-1]
            current_bb_upper = bb_upper.iloc[-1]
            current_bb_lower = bb_lower.iloc[-1]
            current_ema = ema.iloc[-1]
            current_cci = cci.iloc[-1]
            current_stoch_k = stoch_k.iloc[-1]
            
            # Check signals from each indicator
            bb_signal = self.signal_generator.check_bollinger_signal(close, bb_upper, bb_lower)
            ema_signal = self.signal_generator.check_ema_signal(current_close, current_ema)
            cci_signal = self.signal_generator.check_cci_signal(current_cci)
            stoch_signal = self.signal_generator.check_stochastic_signal(current_stoch_k)
            
            # Aggregate signals - all indicators must agree for a signal
            signals = [s for s in [bb_signal, ema_signal, cci_signal, stoch_signal] if s is not None]
            
            # Determine final action
            action = None
            if len(signals) >= 3:  # At least 3 indicators must agree
                call_count = signals.count('call')
                put_count = signals.count('put')
                
                if call_count >= 3:
                    action = 'call'
                elif put_count >= 3:
                    action = 'put'
            
            result = {
                'active': active,
                'action': action,
                'indicators': {
                    'bollinger_bands': {'signal': bb_signal, 'upper': current_bb_upper, 'lower': current_bb_lower},
                    'ema': {'signal': ema_signal, 'value': current_ema},
                    'cci': {'signal': cci_signal, 'value': current_cci},
                    'stochastic': {'signal': stoch_signal, 'k': current_stoch_k}
                },
                'close_price': current_close
            }
            
            # Log the result
            with self.lock:
                if action:
                    logger.info(f"Active={active}, Action={action}")
                else:
                    logger.info(f"Active={active}, Action=None (no clear signal)")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing {active}: {str(e)}")
            return {'active': active, 'action': None, 'error': str(e)}
    
    def process_multiple_actives(self, actives_data: Dict[str, pd.DataFrame]) -> List[Dict[str, any]]:
        """
        Process multiple actives in parallel using threading
        
        Args:
            actives_data: Dictionary mapping active names to their candle DataFrames
            
        Returns:
            List of results for each active
        """
        results = []
        
        logger.info(f"Starting parallel processing of {len(actives_data)} actives")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_active = {
                executor.submit(self.process_active, active, data): active 
                for active, data in actives_data.items()
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_active):
                active = future_to_active[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Exception in thread for {active}: {str(e)}")
                    results.append({'active': active, 'action': None, 'error': str(e)})
        
        logger.info(f"Completed processing {len(results)} actives")
        return results


# Convenience function for external use
def analyze_actives(actives_data: Dict[str, pd.DataFrame], max_workers: int = 5) -> List[Dict[str, any]]:
    """
    Analyze multiple actives and generate trading signals
    
    Args:
        actives_data: Dictionary mapping active names to their candle DataFrames
        max_workers: Maximum number of threads for parallel processing
        
    Returns:
        List of results for each active
    """
    engine = StrategyEngine(max_workers=max_workers)
    return engine.process_multiple_actives(actives_data)


if __name__ == "__main__":
    # Test scenario with mock data
    logger.info("Running test scenario for strategy_super_patron")
    
    # Generate mock candle data for testing
    def generate_mock_data(active_name: str, num_candles: int = 200) -> pd.DataFrame:
        """Generate mock candle data for testing"""
        np.random.seed(hash(active_name) % (2**32))  # Different seed for each active
        
        base_price = 1.0 if 'EUR' in active_name else 100.0
        volatility = base_price * 0.01
        
        prices = [base_price]
        for _ in range(num_candles - 1):
            change = np.random.randn() * volatility
            prices.append(prices[-1] + change)
        
        close = pd.Series(prices)
        high = close + abs(np.random.randn(num_candles) * volatility * 0.5)
        low = close - abs(np.random.randn(num_candles) * volatility * 0.5)
        open_price = close + np.random.randn(num_candles) * volatility * 0.3
        volume = pd.Series(np.random.randint(1000, 10000, num_candles))
        
        return pd.DataFrame({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    # Create test data for multiple actives
    test_actives = ['USDJPY', 'EURUSD']
    test_data = {
        active: generate_mock_data(active) 
        for active in test_actives
    }
    
    # Run the analysis
    logger.info("="*60)
    logger.info("Starting Strategy Super Patron Analysis")
    logger.info("="*60)
    
    results = analyze_actives(test_data, max_workers=2)
    
    # Display results
    logger.info("="*60)
    logger.info("Analysis Results:")
    logger.info("="*60)
    for result in results:
        if result['action']:
            logger.info(f"Active={result['active']}, Action={result['action']}")
        else:
            logger.info(f"Active={result['active']}, Action=None")
