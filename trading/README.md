# Binance Futures Testnet Trading Bot

A clean, production-structured Python CLI for placing orders on the Binance USDT-M Futures Testnet.

---

## Features

-  Market and Limit orders (BUY / SELL)
-  Bonus: Stop-Market orders
-  Input validation with clear error messages
-  Structured logging to rotating log file + console
-  Separate client / order / validator / CLI layers
-  `--dry-run` mode (validate without sending)
-  Account balance summary command
-  Open-orders list command
-  Zero third-party dependencies beyond `requests`

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package exports
│   ├── client.py            # Binance REST client (signing, requests, error handling)
│   ├── orders.py            # Order placement logic + terminal output
│   ├── validators.py        # Input validation
│   └── logging_config.py   # Rotating file + console logger setup
├── cli.py                   # argparse CLI entry point
├── logs/
│   └── trading_bot.log      # Auto-created on first run
├── README.md
└── requirements.txt
```

---

## Setup

### 1. Prerequisites

- Python 3.8+
- A Binance Futures Testnet account

### 2. Get Testnet API Credentials

1. Visit <https://testnet.binancefuture.com>
2. Register / log in
3. Go to **API Management** → **Generate API Key**
4. Copy your **API Key** and **Secret Key**

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Environment Variables

```bash
export BINANCE_TESTNET_API_KEY="your_api_key_here"
export BINANCE_TESTNET_API_SECRET="your_api_secret_here"
```

On Windows (PowerShell):
```powershell
$env:BINANCE_TESTNET_API_KEY="your_api_key_here"
$env:BINANCE_TESTNET_API_SECRET="your_api_secret_here"
```

---

## How to Run

All commands are run from the `trading_bot/` directory:

```
python cli.py <command> [options]
```

### Place a Market Order

```bash
# Market BUY 0.01 BTC
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

# Market SELL 0.5 ETH
python cli.py place --symbol ETHUSDT --side SELL --type MARKET --quantity 0.5
```

### Place a Limit Order

```bash
# Limit BUY 0.01 BTC at $55,000
python cli.py place --symbol BTCUSDT --side BUY --type LIMIT \
    --quantity 0.01 --price 55000

# Limit SELL 0.1 ETH at $3,200 with IOC time-in-force
python cli.py place --symbol ETHUSDT --side SELL --type LIMIT \
    --quantity 0.1 --price 3200 --tif IOC
```

### Place a Stop-Market Order (Bonus)

```bash
# Stop-market SELL 0.01 BTC — triggers at $58,000
python cli.py place --symbol BTCUSDT --side SELL --type STOP_MARKET \
    --quantity 0.01 --stop-price 58000
```

### Dry Run (Preview Without Sending)

```bash
python cli.py place --symbol BTCUSDT --side BUY --type LIMIT \
    --quantity 0.01 --price 55000 --dry-run
```

### View Account Balance

```bash
python cli.py account
```

### List Open Orders

```bash
# All open orders
python cli.py open-orders

# Filtered by symbol
python cli.py open-orders --symbol BTCUSDT
```

### Help

```bash
python cli.py --help
python cli.py place --help
```

---

## Example Terminal Output

```
────────────────────────────────────────────────────────────
  ORDER REQUEST SUMMARY
────────────────────────────────────────────────────────────
  Symbol     : BTCUSDT
  Side       : BUY
  Type       : MARKET
  Quantity   : 0.01
────────────────────────────────────────────────────────────

────────────────────────────────────────────────────────────
  ORDER RESPONSE
────────────────────────────────────────────────────────────
  Order ID      : 4058868516
  Client ID     : x-xcKtGiEu12345678
  Symbol        : BTCUSDT
  Status        : FILLED
  Side          : BUY
  Type          : MARKET
  Orig Qty      : 0.01
  Executed Qty  : 0.01
  Avg Price     : 57823.40
  Time in Force : GTC
  Update Time   : 1720621321512
────────────────────────────────────────────────────────────

  ✓  Order placed successfully! (orderId=4058868516)
```

---

## Logging

Logs are written to `logs/trading_bot.log` (auto-created).

- **File**: DEBUG level and above — full API request/response audit trail, rotating at 5 MB, 3 backups kept.
- **Console**: WARNING level and above by default (set `LOG_LEVEL=DEBUG` to see everything).

```bash
# Verbose console output
LOG_LEVEL=DEBUG python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Missing required flag (`--price` for LIMIT) | Validation error printed before any API call |
| Invalid symbol on exchange | Binance API error code + message displayed |
| Network timeout / connection refused | Network error message displayed |
| Quantity ≤ 0 | Validation error with clear message |
| Missing API credentials | ValueError at startup with instructions |

---

## Assumptions

- Target: **USDT-M Futures Testnet** only (`https://testnet.binancefuture.com`)
- Quantity precision must satisfy the symbol's `LOT_SIZE` filter (use the testnet's own minimums — BTCUSDT accepts 0.001 BTC, ETHUSDT accepts 0.001 ETH)
- `positionSide` defaults to `BOTH` (one-way mode). Hedge mode is not supported.
- Credentials are provided via environment variables (no `.env` file to avoid accidental secrets in source control)
