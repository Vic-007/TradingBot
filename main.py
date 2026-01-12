"""
Main entry point for the IQ Option Trading Bot
Strategy Super Patron - Multi-threaded Binary Options Trading
"""

import logging
import argparse
import sys
from typing import List

from bot import IQOptionBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)


def main(actives: List[str], email: str = None, password: str = None, 
         mock_mode: bool = False, duration: int = 60, candle_count: int = 200, 
         max_workers: int = 5):
    """
    Main function to run the trading bot
    
    Args:
        actives: List of actives to analyze (e.g., ['EURUSD', 'USDJPY'])
        email: IQ Option account email
        password: IQ Option account password
        mock_mode: If True, run in mock mode without connecting to real API
        duration: Candle duration in seconds
        candle_count: Number of candles to retrieve
        max_workers: Maximum number of threads for parallel processing
    """
    logger.info("="*70)
    logger.info(" IQ Option Trading Bot - Strategy Super Patron")
    logger.info("="*70)
    logger.info(f"Actives to analyze: {', '.join(actives)}")
    logger.info(f"Candle duration: {duration} seconds")
    logger.info(f"Candle count: {candle_count}")
    logger.info(f"Max workers: {max_workers}")
    logger.info(f"Mock mode: {mock_mode}")
    logger.info("="*70)
    
    # Initialize bot
    bot = IQOptionBot(email=email, password=password, mock_mode=mock_mode)
    
    # Connect to IQ Option
    if not bot.connect():
        logger.error("Failed to connect to IQ Option. Exiting.")
        sys.exit(1)
    
    try:
        # Run strategy on all actives
        results = bot.run_strategy(
            actives=actives,
            duration=duration,
            count=candle_count,
            max_workers=max_workers
        )
        
        # Display final results
        logger.info("="*70)
        logger.info(" FINAL RESULTS - Trading Signals")
        logger.info("="*70)
        
        signal_count = 0
        for result in results:
            active = result.get('active')
            action = result.get('action')
            
            if action:
                signal_count += 1
                logger.info(f"Active={active}, Action={action}")
                
                # Display indicator details
                if 'indicators' in result:
                    indicators = result['indicators']
                    logger.info(f"  Bollinger Bands: {indicators['bollinger_bands']['signal']}")
                    logger.info(f"  EMA 100: {indicators['ema']['signal']}")
                    logger.info(f"  CCI: {indicators['cci']['signal']}")
                    logger.info(f"  Stochastic: {indicators['stochastic']['signal']}")
            else:
                logger.info(f"Active={active}, Action=None (no clear signal)")
        
        logger.info("="*70)
        logger.info(f"Total signals generated: {signal_count}/{len(results)}")
        logger.info("="*70)
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
    finally:
        # Disconnect
        bot.disconnect()
        logger.info("Bot stopped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='IQ Option Trading Bot - Strategy Super Patron'
    )
    parser.add_argument(
        '--actives',
        nargs='+',
        default=['EURUSD', 'USDJPY'],
        help='List of actives to analyze (default: EURUSD USDJPY)'
    )
    parser.add_argument(
        '--email',
        type=str,
        default=None,
        help='IQ Option account email'
    )
    parser.add_argument(
        '--password',
        type=str,
        default=None,
        help='IQ Option account password'
    )
    parser.add_argument(
        '--mock',
        action='store_true',
        help='Run in mock mode (no real API connection)'
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=60,
        help='Candle duration in seconds (default: 60)'
    )
    parser.add_argument(
        '--candles',
        type=int,
        default=200,
        help='Number of candles to retrieve (default: 200)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=5,
        help='Maximum number of worker threads (default: 5)'
    )
    
    args = parser.parse_args()
    
    # Run main function
    main(
        actives=args.actives,
        email=args.email,
        password=args.password,
        mock_mode=args.mock,
        duration=args.duration,
        candle_count=args.candles,
        max_workers=args.workers
    )
