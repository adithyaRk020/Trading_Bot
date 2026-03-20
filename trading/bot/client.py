from __future__ import annotations

import hashlib
import hmac
import os
import time
from decimal import Decimal
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from .logging_config import get_logger

logger = get_logger("client")

TESTNET_BASE_URL = "https://testnet.binancefuture.com"
DEFAULT_TIMEOUT = 10  # seconds


class BinanceAPIError(Exception):

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"Binance API error {code}: {message}")


class BinanceNetworkError(Exception):
    """Raised on connection / timeout failures."""

 
 
class BinanceFuturesClient:

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_url: str = TESTNET_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.api_key = api_key or os.environ.get("BINANCE_TESTNET_API_KEY", "")
        self.api_secret = api_secret or os.environ.get("BINANCE_TESTNET_API_SECRET", "")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        if not self.api_key or not self.api_secret:
            raise ValueError(
                "API key and secret are required. "
                "Set BINANCE_TESTNET_API_KEY and BINANCE_TESTNET_API_SECRET "
                "environment variables, or pass them explicitly."
            )

        self._session = requests.Session()
        self._session.headers.update({"X-MBX-APIKEY": self.api_key})
        self._time_offset_ms: int = 0
        self._sync_server_time()
        logger.info("BinanceFuturesClient initialised (base_url=%s)", self.base_url)


    def _sync_server_time(self) -> None:
        try:
            url = f"{self.base_url}/fapi/v1/time"
            resp = self._session.get(url, timeout=self.timeout)
            server_time = resp.json().get("serverTime", 0)
            local_time = int(time.time() * 1000)
            self._time_offset_ms = server_time - local_time
            logger.info(
                "Server time synced — offset: %+dms", self._time_offset_ms
            )
        except Exception as exc:
            logger.warning("Could not sync server time: %s — using local clock", exc)
            self._time_offset_ms = 0

    def _sign(self, params: dict) -> dict:
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _timestamp(self) -> int:
        return int(time.time() * 1000) + self._time_offset_ms

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        signed: bool = False,
    ) -> Any:
        params = params or {}
        if signed:
            params["timestamp"] = self._timestamp()
            params = self._sign(params)

        url = f"{self.base_url}{path}"

        # Sanitise params for logging (hide signature)
        log_params = {k: v for k, v in params.items() if k != "signature"}
        logger.debug("→ %s %s  params=%s", method.upper(), path, log_params)

        try:
            if method.upper() in ("GET", "DELETE"):
                response = self._session.request(
                    method, url, params=params, timeout=self.timeout
                )
            else:
                response = self._session.request(
                    method, url, data=params, timeout=self.timeout
                )
        except requests.exceptions.Timeout as exc:
            logger.error("Request timed out: %s %s", method, url)
            raise BinanceNetworkError(f"Request timed out after {self.timeout}s") from exc
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error: %s %s — %s", method, url, exc)
            raise BinanceNetworkError(f"Cannot connect to {self.base_url}") from exc

        logger.debug(
            "← %s  %d  %.0fms",
            path,
            response.status_code,
            response.elapsed.total_seconds() * 1000,
        )

        try:
            data = response.json()
        except ValueError:
            logger.error("Non-JSON response: %s", response.text[:300])
            response.raise_for_status()
            return {}

        if isinstance(data, dict) and "code" in data and data["code"] != 200:
            logger.error("API error response: %s", data)
            raise BinanceAPIError(data["code"], data.get("msg", "Unknown error"))

        if not response.ok:
            logger.error("HTTP %s: %s", response.status_code, data)
            raise BinanceAPIError(response.status_code, str(data))

        logger.debug("Response body: %s", data)
        return data


    def get_exchange_info(self) -> dict:
        
        return self._request("GET", "/fapi/v1/exchangeInfo")

    def get_account_info(self) -> dict:
        
        return self._request("GET", "/fapi/v2/account", signed=True)

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
    ) -> dict:
        
        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": str(quantity),
        }

        if order_type == "LIMIT":
            if price is None:
                raise ValueError("price is required for LIMIT orders")
            params["price"] = str(price)
            params["timeInForce"] = time_in_force

        if order_type in ("STOP", "STOP_MARKET") and stop_price is not None:
            params["stopPrice"] = str(stop_price)
            if order_type == "STOP" and price is not None:
                params["price"] = str(price)
            if order_type == "STOP":
                params["timeInForce"] = time_in_force

        if reduce_only:
            params["reduceOnly"] = "true"

        logger.info(
            "Placing order: %s %s %s qty=%s price=%s",
            order_type, side, symbol, quantity, price,
        )
        response = self._request("POST", "/fapi/v1/order", params=params, signed=True)
        logger.info(
            "Order placed — orderId=%s status=%s",
            response.get("orderId"),
            response.get("status"),
        )
        return response

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        
        params = {"symbol": symbol, "orderId": order_id}
        logger.info("Cancelling orderId=%s on %s", order_id, symbol)
        return self._request("DELETE", "/fapi/v1/order", params=params, signed=True)

    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/openOrders", params=params, signed=True)