"""
Test module for Strategy Super Patron
Tests indicator calculations and signal generation with mock data
"""

import unittest
import pandas as pd
import numpy as np
from strategy_super_patron import (
    StrategyIndicators, 
    SignalGenerator, 
    StrategyEngine,
    analyze_actives
)


class TestStrategyIndicators(unittest.TestCase):
    """Test indicator calculations"""
    
    def setUp(self):
        """Set up test data"""
        np.random.seed(42)
        self.close_prices = pd.Series(np.random.randn(200).cumsum() + 100)
        self.high_prices = self.close_prices + abs(np.random.randn(200) * 0.5)
        self.low_prices = self.close_prices - abs(np.random.randn(200) * 0.5)
        self.indicators = StrategyIndicators()
    
    def test_bollinger_bands(self):
        """Test Bollinger Bands calculation"""
        upper, middle, lower = self.indicators.calculate_bollinger_bands(self.close_prices, period=6, deviation=2.0)
        
        self.assertEqual(len(upper), len(self.close_prices))
        self.assertEqual(len(middle), len(self.close_prices))
        self.assertEqual(len(lower), len(self.close_prices))
        
        # Check that upper > middle > lower (for non-NaN values)
        valid_idx = ~pd.isna(upper)
        self.assertTrue((upper[valid_idx] >= middle[valid_idx]).all())
        self.assertTrue((middle[valid_idx] >= lower[valid_idx]).all())
    
    def test_ema(self):
        """Test EMA calculation"""
        ema = self.indicators.calculate_ema(self.close_prices, period=100)
        
        self.assertEqual(len(ema), len(self.close_prices))
        # First values should be NaN due to period requirement
        self.assertTrue(pd.isna(ema.iloc[0]))
        # Later values should be valid
        self.assertFalse(pd.isna(ema.iloc[-1]))
    
    def test_cci(self):
        """Test CCI calculation"""
        cci = self.indicators.calculate_cci(self.high_prices, self.low_prices, self.close_prices, period=14)
        
        self.assertEqual(len(cci), len(self.close_prices))
        # Later values should be valid
        self.assertFalse(pd.isna(cci.iloc[-1]))
    
    def test_stochastic(self):
        """Test Stochastic Oscillator calculation"""
        stoch_k, stoch_d = self.indicators.calculate_stochastic(
            self.high_prices, self.low_prices, self.close_prices,
            fastk_period=13, slowk_period=3, slowd_period=3
        )
        
        self.assertEqual(len(stoch_k), len(self.close_prices))
        self.assertEqual(len(stoch_d), len(self.close_prices))
        # Later values should be valid
        self.assertFalse(pd.isna(stoch_k.iloc[-1]))
        self.assertFalse(pd.isna(stoch_d.iloc[-1]))


class TestSignalGenerator(unittest.TestCase):
    """Test signal generation logic"""
    
    def setUp(self):
        """Set up test data"""
        self.signal_generator = SignalGenerator()
    
    def test_bollinger_signal_call(self):
        """Test Bollinger Bands call signal"""
        close_prices = pd.Series([100, 95, 90])
        bb_upper = pd.Series([110, 110, 110])
        bb_lower = pd.Series([91, 91, 91])  # Price crosses below lower band
        
        signal = self.signal_generator.check_bollinger_signal(close_prices, bb_upper, bb_lower)
        self.assertEqual(signal, 'call')
    
    def test_bollinger_signal_put(self):
        """Test Bollinger Bands put signal"""
        close_prices = pd.Series([100, 105, 112])
        bb_upper = pd.Series([110, 110, 110])  # Price crosses above upper band
        bb_lower = pd.Series([90, 90, 90])
        
        signal = self.signal_generator.check_bollinger_signal(close_prices, bb_upper, bb_lower)
        self.assertEqual(signal, 'put')
    
    def test_ema_signal_call(self):
        """Test EMA call signal"""
        signal = self.signal_generator.check_ema_signal(close_price=105, ema_value=100)
        self.assertEqual(signal, 'call')  # EMA below price
    
    def test_ema_signal_put(self):
        """Test EMA put signal"""
        signal = self.signal_generator.check_ema_signal(close_price=95, ema_value=100)
        self.assertEqual(signal, 'put')  # EMA above price
    
    def test_cci_signal_call(self):
        """Test CCI call signal (oversold)"""
        signal = self.signal_generator.check_cci_signal(cci_value=-150)
        self.assertEqual(signal, 'call')
    
    def test_cci_signal_put(self):
        """Test CCI put signal (overbought)"""
        signal = self.signal_generator.check_cci_signal(cci_value=150)
        self.assertEqual(signal, 'put')
    
    def test_cci_signal_none(self):
        """Test CCI no signal"""
        signal = self.signal_generator.check_cci_signal(cci_value=50)
        self.assertIsNone(signal)
    
    def test_stochastic_signal_call(self):
        """Test Stochastic call signal (oversold)"""
        signal = self.signal_generator.check_stochastic_signal(stoch_k=15)
        self.assertEqual(signal, 'call')
    
    def test_stochastic_signal_put(self):
        """Test Stochastic put signal (overbought)"""
        signal = self.signal_generator.check_stochastic_signal(stoch_k=85)
        self.assertEqual(signal, 'put')
    
    def test_stochastic_signal_none(self):
        """Test Stochastic no signal"""
        signal = self.signal_generator.check_stochastic_signal(stoch_k=50)
        self.assertIsNone(signal)


class TestStrategyEngine(unittest.TestCase):
    """Test strategy engine and parallel processing"""
    
    def setUp(self):
        """Set up test data"""
        self.engine = StrategyEngine(max_workers=2)
    
    def generate_mock_data(self, num_candles=200, base_price=100):
        """Generate mock candle data"""
        np.random.seed(42)
        close = pd.Series(np.random.randn(num_candles).cumsum() + base_price)
        high = close + abs(np.random.randn(num_candles) * 0.5)
        low = close - abs(np.random.randn(num_candles) * 0.5)
        open_price = close + np.random.randn(num_candles) * 0.3
        volume = pd.Series(np.random.randint(1000, 10000, num_candles))
        
        return pd.DataFrame({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    def test_process_single_active(self):
        """Test processing a single active"""
        candle_data = self.generate_mock_data()
        result = self.engine.process_active('EURUSD', candle_data)
        
        self.assertIn('active', result)
        self.assertEqual(result['active'], 'EURUSD')
        self.assertIn('action', result)
        self.assertIn('indicators', result)
    
    def test_process_multiple_actives(self):
        """Test parallel processing of multiple actives"""
        actives_data = {
            'EURUSD': self.generate_mock_data(base_price=1.0),
            'USDJPY': self.generate_mock_data(base_price=110.0)
        }
        
        results = self.engine.process_multiple_actives(actives_data)
        
        self.assertEqual(len(results), 2)
        actives_in_results = [r['active'] for r in results]
        self.assertIn('EURUSD', actives_in_results)
        self.assertIn('USDJPY', actives_in_results)
    
    def test_insufficient_data(self):
        """Test handling of insufficient data"""
        # Create data with only 50 candles (less than required 100)
        candle_data = self.generate_mock_data(num_candles=50)
        result = self.engine.process_active('EURUSD', candle_data)
        
        self.assertIn('error', result)
        self.assertIsNone(result['action'])


class TestAnalyzeActives(unittest.TestCase):
    """Test the convenience function"""
    
    def generate_mock_data(self, num_candles=200, base_price=100):
        """Generate mock candle data"""
        np.random.seed(42)
        close = pd.Series(np.random.randn(num_candles).cumsum() + base_price)
        high = close + abs(np.random.randn(num_candles) * 0.5)
        low = close - abs(np.random.randn(num_candles) * 0.5)
        open_price = close + np.random.randn(num_candles) * 0.3
        volume = pd.Series(np.random.randint(1000, 10000, num_candles))
        
        return pd.DataFrame({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    def test_analyze_actives_function(self):
        """Test the analyze_actives convenience function"""
        actives_data = {
            'EURUSD': self.generate_mock_data(base_price=1.0),
            'USDJPY': self.generate_mock_data(base_price=110.0)
        }
        
        results = analyze_actives(actives_data, max_workers=2)
        
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertIn('active', result)
            self.assertIn('action', result)


if __name__ == '__main__':
    unittest.main()
