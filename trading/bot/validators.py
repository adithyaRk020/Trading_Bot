from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET", "STOP"}
VALID_SIDES = {"BUY", "SELL"}

MIN_QUANTITY = Decimal("0.001")
MIN_PRICE = Decimal("0.01")


def validate_symbol(symbol: str) -> str:
    """Return upper-cased symbol or raise ValueError."""
    symbol = symbol.strip().upper()
    if not symbol.isalnum():
        raise ValueError(
            f"Symbol '{symbol}' contains invalid characters. "
            "Expected something like BTCUSDT or ETHUSDT."
        )
    if len(symbol) < 3 or len(symbol) > 20:
        raise ValueError(f"Symbol '{symbol}' length is unusual. Double-check the ticker.")
    return symbol


def validate_side(side: str) -> str:
    """Return normalised side or raise ValueError."""
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Choose from: {', '.join(sorted(VALID_SIDES))}."
        )
    return side


def validate_order_type(order_type: str) -> str:
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Supported types: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return order_type


def validate_quantity(quantity: str | float | Decimal) -> Decimal:
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValueError(f"Quantity '{quantity}' is not a valid number.")
    if qty <= 0:
        raise ValueError("Quantity must be greater than zero.")
    if qty < MIN_QUANTITY:
        raise ValueError(
            f"Quantity {qty} is below the minimum allowed value of {MIN_QUANTITY}."
        )
    return qty


def validate_price(price: str | float | Decimal | None) -> Optional[Decimal]:
    
    if price is None:
        return None
    price_str = str(price).strip()
    if price_str == "":
        return None
    try:
        p = Decimal(price_str)
    except InvalidOperation:
        raise ValueError(f"Price '{price}' is not a valid number.")
    if p <= 0:
        raise ValueError("Price must be greater than zero.")
    if p < MIN_PRICE:
        raise ValueError(f"Price {p} is below the minimum allowed value of {MIN_PRICE}.")
    return p


def validate_stop_price(stop_price: str | float | Decimal | None) -> Optional[Decimal]:
    return validate_price(stop_price) 


def validate_order_params(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: Optional[str] = None,
    stop_price: Optional[str] = None,
) -> dict:
    
    cleaned_symbol = validate_symbol(symbol)
    cleaned_side = validate_side(side)
    cleaned_type = validate_order_type(order_type)
    cleaned_qty = validate_quantity(quantity)
    cleaned_price = validate_price(price)
    cleaned_stop = validate_stop_price(stop_price)

    if cleaned_type == "LIMIT" and cleaned_price is None:
        raise ValueError("A price is required for LIMIT orders.")

    if cleaned_type in ("STOP", "STOP_MARKET") and cleaned_stop is None:
        raise ValueError(f"A stop price is required for {cleaned_type} orders.")

    if cleaned_type == "MARKET" and cleaned_price is not None:
        pass

    return {
        "symbol": cleaned_symbol,
        "side": cleaned_side,
        "order_type": cleaned_type,
        "quantity": cleaned_qty,
        "price": cleaned_price,
        "stop_price": cleaned_stop,
    }
