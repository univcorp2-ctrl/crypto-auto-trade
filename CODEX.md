# Agent Notes

## Commands

```bash
pip install -e '.[dev,web,live]'
ruff check .
pytest -q
python -m crypto_auto_trade.cli validate --iterations 200 --trailing-stop-pct 0.05
python -m crypto_auto_trade.web
```

## Hard rule

After any BUY that creates a position, a trailing stop must be armed and updated while the position exists.

## Guardrails

- Never commit secrets.
- Keep live trading blocked unless ACK and exchange keys are set.
- Any new strategy must work in backtest, forward test, realtime validation, and UI comparison.
- Prefer simple UI changes over complex frameworks.
