# TradingBot
Bot to trade Binary Options using IQ Option API

## Strategy Super Patron

This bot implements a multi-threaded binary options trading strategy using technical indicators to identify entry points.

### Features

- **Multi-threaded Processing**: Analyze multiple currency pairs (actives) concurrently
- **Technical Indicators**:
  - Bollinger Bands (period=6, deviation=2)
  - EMA 100 (Exponential Moving Average)
  - CCI (Commodity Channel Index, period=14)
  - Stochastic Oscillator (K=13, smoothing=3, D=3)
- **Signal Generation**: Automated call/put signal detection
- **Text-based Logging**: Clear status updates and signal notifications

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install TA-Lib (required for technical indicators):
   - On Ubuntu/Debian: `sudo apt-get install ta-lib`
   - On macOS: `brew install ta-lib`
   - For Windows or other systems, see: https://github.com/mrjbq7/ta-lib

### Usage

#### Mock Mode (Testing)
Run the bot with mock data (no API credentials required):
```bash
python main.py --mock --actives EURUSD USDJPY GBPUSD
```

#### Live Mode
Run with real IQ Option API credentials:
```bash
python main.py --email your_email@example.com --password your_password --actives EURUSD USDJPY
```

#### Options
- `--actives`: List of currency pairs to analyze (default: EURUSD USDJPY)
- `--email`: IQ Option account email
- `--password`: IQ Option account password
- `--mock`: Run in mock mode without API connection
- `--duration`: Candle duration in seconds (default: 60)
- `--candles`: Number of candles to retrieve (default: 200)
- `--workers`: Maximum number of worker threads (default: 5)

### Testing

Run unit tests:
```bash
python test_strategy.py
```

Run the strategy module directly (mock scenario):
```bash
python strategy_super_patron.py
```

Run the bot module directly (mock scenario):
```bash
python bot.py
```

### How It Works

1. **Data Collection**: The bot fetches historical candle data for each active
2. **Indicator Calculation**: Each active is processed in a separate thread:
   - Bollinger Bands detect price extremes
   - EMA 100 identifies trend direction
   - CCI detects oversold/overbought conditions
   - Stochastic Oscillator confirms momentum
3. **Signal Generation**: 
   - **CALL Signal**: Price below lower Bollinger Band, EMA below price, CCI < -100, Stochastic < 20
   - **PUT Signal**: Price above upper Bollinger Band, EMA above price, CCI > 100, Stochastic > 80
4. **Consensus**: At least 3 out of 4 indicators must agree for a signal to be generated

### Output Format

```
Active=EURUSD, Action=call
Active=USDJPY, Action=put
Active=GBPUSD, Action=None (no clear signal)
```

### Module Structure

- `strategy_super_patron.py`: Core strategy logic with indicators and signal generation
- `bot.py`: IQ Option API integration and data fetching
- `main.py`: Main entry point with command-line interface
- `test_strategy.py`: Unit tests for strategy components
- `requirements.txt`: Python dependencies

### Requirements

- Python 3.7+
- TA-Lib library
- pandas, pandas-ta, numpy
- IQ Option API (iqoptionapi)
- matplotlib (for potential visualization)

### License

This project is for educational purposes. Use at your own risk. Binary options trading involves significant risk.
