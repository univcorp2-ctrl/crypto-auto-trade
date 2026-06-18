# Setup

```bash
git clone https://github.com/univcorp2-ctrl/crypto-auto-trade.git
cd crypto-auto-trade
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,web,live]'
pytest
python -m crypto_auto_trade.cli validate --iterations 200
python -m crypto_auto_trade.web
```

Open `http://127.0.0.1:8000`.

The UI contains a `Trailing Stop %` field. This value is passed into backtest, forward test, realtime validation, and paper trading.
