# XAUUSD Wolf Market Scanner

Step 1 is a local, read-only dashboard that verifies a Python connection to MetaTrader 5, finds an available XAUUSD broker symbol, and displays live quotes with recent raw candles for configured timeframes.

This project is analysis only. It does not place trades or provide financial advice. It includes explainable market signals and fixed-horizon historical signal validation; neither represents execution or a profitability claim.

## Requirements

- Windows with Python 3.12 or newer
- A locally installed MetaTrader 5 terminal, running and logged in to a broker account
- The terminal's XAUUSD symbol available in Market Watch

## Install

In PowerShell, from the project folder:

```powershell
cd d:\Trading\XAUUSD-WOLF-SCANNER
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Install MetaTrader 5 from your broker or MetaQuotes, sign in, and keep the terminal running before launching the scanner.

## Configure

Copy `.env.example` to `.env` only when terminal or account details are needed. Do not commit `.env`.

```powershell
Copy-Item .env.example .env
```

Set `MT5_TERMINAL_PATH` when Python cannot locate the terminal. Use `MT5_LOGIN`, `MT5_PASSWORD`, and `MT5_SERVER` only if automatic terminal authentication is required. `MT5_SYMBOL` overrides the default preferred symbol.

`config.yaml` controls symbol candidates, displayed timeframes, candle count, and refresh interval. Environment values override matching MT5 values in YAML.

The `market_status` section controls freshness thresholds and the initial weekly XAUUSD session policy. Its default is a UTC window from Sunday 22:00 until Friday 22:00. It is a sensible baseline only: brokers can use different sessions, maintenance windows, holidays, and daylight-saving rules. Adjust the configured session values to match your broker.

If no XAUUSD symbol is found, open MetaTrader 5 Market Watch and inspect the broker's naming convention. Add its exact symbol to `market.symbol_candidates` in `config.yaml`, then restart the dashboard.

## Run

```powershell
python run.py
```

Or launch directly:

```powershell
streamlit run app/main.py
```

Streamlit displays the local URL after startup, normally `http://localhost:8501`.

## Test

```powershell
python -m pytest
```

The unit tests mock the MetaTrader 5 API and do not need a terminal. Live prices, broker symbol discovery, terminal connectivity, and candle retrieval must be verified against your local MetaTrader 5 installation.

## Streamlit Community Cloud

Deploy with this entrypoint:

```text
app/main.py
```

The Cloud environment is Linux and cannot connect to a locally installed Windows MetaTrader 5 terminal. `MetaTrader5` is therefore installed only on Windows. On Community Cloud the app starts safely but reports that live MT5 data is unavailable; use injected historical data for backtesting. No Streamlit secrets are currently required. If you later configure MT5 credentials locally, keep them in `.env` and never commit it.

## Current limitations

Live quotes and live indicator/signal display require a locally installed, running MT5 terminal on Windows. Community Cloud cannot provide this local-terminal integration. Backtest results are theoretical directional validation and do not model actual broker execution beyond any configured optional costs.

## Indicator Engine

The indicator engine calculates raw trend, momentum, volatility, structure, and candle values for each timeframe independently. Parameters live under `indicators` in `config.yaml`. The dashboard presents M5 and M15 values from the latest completed candle; warm-up values remain unavailable until enough history exists. Confirmed swings are recorded only on the later candle that confirms an earlier pivot, so the engine does not retroactively use future candle data.
