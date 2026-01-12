"""
Bot Module for IQ Option Integration
Handles connection to IQ Option API and fetches candle data for actives
"""

import logging
import time
from typing import Dict, List, Optional
from datetime import datetime

import pandas as pd

try:
    from iqoptionapi.stable_api import IQ_Option
    IQ_OPTION_AVAILABLE = True
except ImportError:
    IQ_OPTION_AVAILABLE = False
    logging.warning("IQ Option API not available. Mock mode will be used.")

from strategy_super_patron import analyze_actives

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IQOptionBot:
    """Bot for interfacing with IQ Option API"""
    
    def __init__(self, email: Optional[str] = None, password: Optional[str] = None, mock_mode: bool = False):
        """
        Initialize IQ Option Bot
        
        Args:
            email: IQ Option account email
            password: IQ Option account password
            mock_mode: If True, use mock data instead of real API
        """
        self.email = email
        self.password = password
        self.mock_mode = mock_mode or not IQ_OPTION_AVAILABLE
        self.api = None
        self.connected = False
        
        if not self.mock_mode and IQ_OPTION_AVAILABLE:
            try:
                self.api = IQ_Option(email, password)
                logger.info("IQ Option API initialized")
            except Exception as e:
                logger.error(f"Failed to initialize IQ Option API: {e}")
                self.mock_mode = True
        else:
            logger.info("Running in MOCK mode")
    
    def connect(self) -> bool:
        """
        Connect to IQ Option API
        
        Returns:
            True if connected successfully, False otherwise
        """
        if self.mock_mode:
            logger.info("Mock mode: Connection simulated")
            self.connected = True
            return True
        
        try:
            check, reason = self.api.connect()
            if check:
                logger.info("Successfully connected to IQ Option")
                self.connected = True
                return True
            else:
                logger.error(f"Failed to connect to IQ Option: {reason}")
                return False
        except Exception as e:
            logger.error(f"Exception during connection: {e}")
            return False
    
    def get_candles(self, active: str, duration: int = 60, count: int = 200) -> Optional[pd.DataFrame]:
        """
        Get candle data for an active
        
        Args:
            active: Active name (e.g., 'EURUSD', 'USDJPY')
            duration: Candle duration in seconds (default: 60)
            count: Number of candles to retrieve (default: 200)
            
        Returns:
            DataFrame with candle data or None if failed
        """
        if self.mock_mode:
            return self._generate_mock_candles(active, count)
        
        try:
            end_time = time.time()
            candles = self.api.get_candles(active, duration, count, end_time)
            
            if candles:
                df = pd.DataFrame(candles)
                # Standardize column names
                df = df.rename(columns={
                    'from': 'timestamp',
                    'open': 'open',
                    'max': 'high',
                    'min': 'low',
                    'close': 'close',
                    'volume': 'volume'
                })
                logger.info(f"Retrieved {len(df)} candles for {active}")
                return df[['open', 'high', 'low', 'close', 'volume']]
            else:
                logger.warning(f"No candles retrieved for {active}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting candles for {active}: {e}")
            return None
    
    def _generate_mock_candles(self, active: str, count: int = 200) -> pd.DataFrame:
        """
        Generate mock candle data for testing
        
        Args:
            active: Active name
            count: Number of candles to generate
            
        Returns:
            DataFrame with mock candle data
        """
        import numpy as np
        
        # Set seed based on active name for reproducibility
        np.random.seed(hash(active) % (2**32))
        
        base_price = 1.0 if 'EUR' in active or 'GBP' in active else 100.0
        volatility = base_price * 0.01
        
        prices = [base_price]
        for _ in range(count - 1):
            change = np.random.randn() * volatility
            prices.append(max(prices[-1] + change, base_price * 0.5))  # Prevent negative prices
        
        close = pd.Series(prices)
        high = close + abs(np.random.randn(count) * volatility * 0.5)
        low = close - abs(np.random.randn(count) * volatility * 0.5)
        open_price = close + np.random.randn(count) * volatility * 0.3
        volume = pd.Series(np.random.randint(1000, 10000, count))
        
        return pd.DataFrame({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    def fetch_actives_data(self, actives: List[str], duration: int = 60, count: int = 200) -> Dict[str, pd.DataFrame]:
        """
        Fetch candle data for multiple actives
        
        Args:
            actives: List of active names
            duration: Candle duration in seconds
            count: Number of candles to retrieve
            
        Returns:
            Dictionary mapping active names to their candle DataFrames
        """
        actives_data = {}
        
        for active in actives:
            logger.info(f"Fetching data for {active}")
            candles = self.get_candles(active, duration, count)
            if candles is not None:
                actives_data[active] = candles
            else:
                logger.warning(f"Skipping {active} due to data fetch failure")
        
        return actives_data
    
    def run_strategy(self, actives: List[str], duration: int = 60, count: int = 200, max_workers: int = 5) -> List[Dict]:
        """
        Run the Super Patron strategy on multiple actives
        
        Args:
            actives: List of active names to analyze
            duration: Candle duration in seconds
            count: Number of candles to retrieve
            max_workers: Maximum number of threads for parallel processing
            
        Returns:
            List of analysis results
        """
        if not self.connected:
            logger.error("Not connected to IQ Option. Call connect() first.")
            return []
        
        # Fetch data for all actives
        logger.info(f"Fetching data for {len(actives)} actives")
        actives_data = self.fetch_actives_data(actives, duration, count)
        
        if not actives_data:
            logger.error("No data retrieved for any active")
            return []
        
        # Run strategy analysis
        logger.info("Running strategy analysis")
        results = analyze_actives(actives_data, max_workers)
        
        return results
    
    def disconnect(self):
        """Disconnect from IQ Option API"""
        if not self.mock_mode and self.api:
            try:
                # IQ Option API doesn't have explicit disconnect, just cleanup
                logger.info("Disconnecting from IQ Option")
                self.connected = False
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
        else:
            logger.info("Mock mode: Disconnection simulated")
            self.connected = False


if __name__ == "__main__":
    # Test scenario
    logger.info("="*60)
    logger.info("Testing IQ Option Bot with Strategy Super Patron")
    logger.info("="*60)
    
    # Create bot in mock mode
    bot = IQOptionBot(mock_mode=True)
    
    # Connect
    if bot.connect():
        # Define actives to analyze
        test_actives = ['USDJPY', 'EURUSD', 'GBPUSD']
        
        # Run strategy
        results = bot.run_strategy(test_actives, duration=60, count=200, max_workers=3)
        
        # Display results
        logger.info("="*60)
        logger.info("Strategy Results:")
        logger.info("="*60)
        for result in results:
            if result.get('action'):
                logger.info(f"Active={result['active']}, Action={result['action']}")
            else:
                logger.info(f"Active={result['active']}, Action=None (no clear signal)")
        
        # Disconnect
        bot.disconnect()
    else:
        logger.error("Failed to connect to IQ Option")
