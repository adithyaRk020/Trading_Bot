#!/usr/bin/env python3
"""
cli.py — Command-line interface for the Binance Futures Testnet trading bot.

Usage examples:
    # Market buy
    python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

    # Limit sell
    python cli.py place --symbol ETHUSDT --side SELL --type LIMIT \
        --quantity 0.1 --price 3200.00

    # Stop-market (bonus)
    python cli.py place --symbol BTCUSDT --side SELL --type STOP_MARKET \
        --quantity 0.01 --stop-price 58000

    # Dry run (no order sent)
    python cli.py place --symbol BTCUSDT --side BUY --type MARKET \
        --quantity 0.01 --dry-run

    # Account info
    python cli.py account

    # List open orders
    python cli.py open-orders --symbol BTCUSDT
"""

import argparse
import os
import sys
from pathlib import Path


def _load_env_file() -> None:
    """
    Load key=value pairs from a .env file in the project root into os.environ.
    Skips blank lines and comments. Does NOT override already-set variables.
    No third-party dependencies required.
    """
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_env_file()  # must run before other imports that read env vars

from bot.client import BinanceFuturesClient, BinanceAPIError, BinanceNetworkError
from bot.logging_config import setup_logging, get_logger
from bot.orders import place_order

# ── Bootstrap logging before anything else ───────────────────────────────────
setup_logging(log_level=os.environ.get("LOG_LEVEL", "WARNING"))
logger = get_logger("cli")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_client() -> BinanceFuturesClient:
    """Construct client from environment variables."""
    return BinanceFuturesClient(
        api_key=os.environ.get("BINANCE_TESTNET_API_KEY"),
        api_secret=os.environ.get("BINANCE_TESTNET_API_SECRET"),
    )


def _print_kv(label: str, value: object, width: int = 22) -> None:
    print(f"  {label:<{width}}: {value}")


# ── Sub-command handlers ──────────────────────────────────────────────────────

def cmd_place(args: argparse.Namespace) -> int:
    """Handle the 'place' sub-command."""
    logger.info(
        "CLI place command: symbol=%s side=%s type=%s qty=%s price=%s stop=%s",
        args.symbol, args.side, args.type, args.quantity, args.price, args.stop_price,
    )

    # Defer client construction until after validation; dry-run never calls the API
    client = None if args.dry_run else _build_client()

    result = place_order(
        client=client,
        symbol=args.symbol,
        side=args.side,
        order_type=args.type,
        quantity=args.quantity,
        price=args.price,
        stop_price=args.stop_price,
        time_in_force=args.time_in_force,
        reduce_only=args.reduce_only,
        dry_run=args.dry_run,
    )
    return 0 if (result is not None or args.dry_run) else 1


def cmd_account(args: argparse.Namespace) -> int:
    """Handle the 'account' sub-command — show balance summary."""
    client = _build_client()
    try:
        info = client.get_account_info()
    except (BinanceAPIError, BinanceNetworkError) as exc:
        print(f"\n  ✗  {exc}\n")
        return 1

    print("\n" + "─" * 60)
    print("  ACCOUNT SUMMARY")
    print("─" * 60)
    _print_kv("Total Wallet Balance", info.get("totalWalletBalance"))
    _print_kv("Unrealised PNL", info.get("totalUnrealizedProfit"))
    _print_kv("Margin Balance", info.get("totalMarginBalance"))
    _print_kv("Available Balance", info.get("availableBalance"))
    print("─" * 60 + "\n")
    return 0


def cmd_open_orders(args: argparse.Namespace) -> int:
    """Handle the 'open-orders' sub-command."""
    client = _build_client()
    try:
        orders = client.get_open_orders(symbol=args.symbol)
    except (BinanceAPIError, BinanceNetworkError) as exc:
        print(f"\n  ✗  {exc}\n")
        return 1

    if not orders:
        print("\n  No open orders found.\n")
        return 0

    print(f"\n{'─'*60}")
    print(f"  OPEN ORDERS ({len(orders)} found)")
    print(f"{'─'*60}")
    for o in orders:
        print(
            f"  [{o['orderId']}] {o['side']:4s} {o['type']:12s} "
            f"{o['symbol']} qty={o['origQty']} price={o['price']} "
            f"status={o['status']}"
        )
    print(f"{'─'*60}\n")
    return 0


# ── Argument parser ───────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet trading bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ── place ─────────────────────────────────────────────────────────────
    place_p = sub.add_parser("place", help="Place a new futures order")
    place_p.add_argument(
        "--symbol", "-s",
        required=True,
        metavar="SYMBOL",
        help="Trading pair, e.g. BTCUSDT",
    )
    place_p.add_argument(
        "--side",
        required=True,
        choices=["BUY", "SELL"],
        type=str.upper,
        help="Order side",
    )
    place_p.add_argument(
        "--type", "-t",
        required=True,
        dest="type",
        choices=["MARKET", "LIMIT", "STOP_MARKET", "STOP"],
        type=str.upper,
        help="Order type",
    )
    place_p.add_argument(
        "--quantity", "-q",
        required=True,
        metavar="QTY",
        help="Order quantity (base asset, e.g. 0.01 for BTC)",
    )
    place_p.add_argument(
        "--price", "-p",
        default=None,
        metavar="PRICE",
        help="Limit price (required for LIMIT / STOP orders)",
    )
    place_p.add_argument(
        "--stop-price",
        default=None,
        metavar="STOP_PRICE",
        dest="stop_price",
        help="Stop / trigger price (required for STOP / STOP_MARKET orders)",
    )
    place_p.add_argument(
        "--tif",
        default="GTC",
        dest="time_in_force",
        choices=["GTC", "IOC", "FOK"],
        help="Time in force for LIMIT orders (default: GTC)",
    )
    place_p.add_argument(
        "--reduce-only",
        action="store_true",
        default=False,
        dest="reduce_only",
        help="Submit as reduce-only order",
    )
    place_p.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        dest="dry_run",
        help="Validate and preview the order without submitting it",
    )
    place_p.set_defaults(func=cmd_place)

    # ── account ───────────────────────────────────────────────────────────
    acct_p = sub.add_parser("account", help="Show account balance summary")
    acct_p.set_defaults(func=cmd_account)

    # ── open-orders ───────────────────────────────────────────────────────
    oo_p = sub.add_parser("open-orders", help="List open orders")
    oo_p.add_argument(
        "--symbol", "-s",
        default=None,
        metavar="SYMBOL",
        help="Filter by symbol (optional)",
    )
    oo_p.set_defaults(func=cmd_open_orders)

    return parser


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
