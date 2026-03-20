from __future__ import annotations

import json
from decimal import Decimal
from typing import Optional

from .client import BinanceAPIError, BinanceFuturesClient, BinanceNetworkError
from .logging_config import get_logger
from .validators import validate_order_params

logger = get_logger("orders")



def _separator(char: str = "─", width: int = 60) -> str:
    return char * width


def _print_request_summary(params: dict) -> None:
    print()
    print(_separator())
    print("  ORDER REQUEST SUMMARY")
    print(_separator())
    print(f"  Symbol     : {params['symbol']}")
    print(f"  Side       : {params['side']}")
    print(f"  Type       : {params['order_type']}")
    print(f"  Quantity   : {params['quantity']}")
    if params.get("price"):
        print(f"  Price      : {params['price']}")
    if params.get("stop_price"):
        print(f"  Stop Price : {params['stop_price']}")
    print(_separator())


def _print_order_response(response: dict) -> None:
    print()
    print(_separator())
    print("  ORDER RESPONSE")
    print(_separator())
    print(f"  Order ID      : {response.get('orderId', 'N/A')}")
    print(f"  Client ID     : {response.get('clientOrderId', 'N/A')}")
    print(f"  Symbol        : {response.get('symbol', 'N/A')}")
    print(f"  Status        : {response.get('status', 'N/A')}")
    print(f"  Side          : {response.get('side', 'N/A')}")
    print(f"  Type          : {response.get('type', 'N/A')}")
    print(f"  Orig Qty      : {response.get('origQty', 'N/A')}")
    print(f"  Executed Qty  : {response.get('executedQty', 'N/A')}")

    avg_price = response.get("avgPrice") or response.get("price") or "N/A"
    print(f"  Avg Price     : {avg_price}")

    if response.get("stopPrice") and response["stopPrice"] != "0":
        print(f"  Stop Price    : {response['stopPrice']}")

    print(f"  Time in Force : {response.get('timeInForce', 'N/A')}")
    print(f"  Update Time   : {response.get('updateTime', 'N/A')}")
    print(_separator())



def place_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: Optional[str] = None,
    stop_price: Optional[str] = None,
    time_in_force: str = "GTC",
    reduce_only: bool = False,
    dry_run: bool = False,
) -> Optional[dict]:
    
    try:
        params = validate_order_params(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
        )
    except ValueError as exc:
        logger.error("Validation failed: %s", exc)
        print(f"\n  ✗  Validation error: {exc}\n")
        return None

    _print_request_summary(params)

    if dry_run:
        print("  [DRY RUN] — no order was sent to the exchange.\n")
        logger.info("Dry-run mode; skipping API call for %s", params)
        return None

    try:
        response = client.place_order(
            symbol=params["symbol"],
            side=params["side"],
            order_type=params["order_type"],
            quantity=params["quantity"],
            price=params.get("price"),
            stop_price=params.get("stop_price"),
            time_in_force=time_in_force,
            reduce_only=reduce_only,
        )
    except BinanceAPIError as exc:
        logger.error("API error placing order: code=%s msg=%s", exc.code, exc.message)
        print(f"\n  ✗  API Error [{exc.code}]: {exc.message}\n")
        return None
    except BinanceNetworkError as exc:
        logger.error("Network error placing order: %s", exc)
        print(f"\n  ✗  Network Error: {exc}\n")
        return None
    except Exception as exc:  
        logger.exception("Unexpected error placing order")
        print(f"\n  ✗  Unexpected error: {exc}\n")
        return None

    _print_order_response(response)
    print(f"\n  ✓  Order placed successfully! (orderId={response.get('orderId')})\n")
    return response
