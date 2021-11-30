from typing import Callable, Dict, List, Optional

import hmac
import hashlib
import json
import requests
import urllib
import time
import logging

from threading import Thread

import websocket
from websocket import WebSocketApp, WebSocketConnectionClosedException

from .enumerations import ProductCode, Channel, PublicChannel
from .requests import ChildOrderRequest
from .responses import Ticker, Balance, Position, ChildOrderResponse

logger = logging.getLogger(__name__)


class BitFlyer:
    URL_BASE = 'https://api.bitflyer.com'
    API_VERSION = 'v1'

    def __init__(self, access_key: Optional[str] = None, access_secret: Optional[str] = None) -> None:
        self._access_key = access_key
        self._access_secret = access_secret

    def get_ticker(self, product_code: ProductCode) -> Ticker:
        response = self._request('GET', 'ticker', request_params={'product_code': product_code.name}, auth=False)
        return Ticker.from_dict(response.json())

    def _get_auth_header(
            self, http_method: str, request_path: str, request_body: str, request_params: Dict,
    ) -> Dict[str, str]:
        if not self._access_key or not self._access_secret:
            raise requests.exceptions.HTTPError('No credential is configured')

        payload = request_body
        if http_method.upper() != 'POST' and request_params:
            payload = f'?{urllib.parse.urlencode(request_params)}'

        access_timestamp = str(time.time())
        text = f'{access_timestamp}{http_method.upper()}{request_path}{payload}'
        access_sign = hmac.new(self._access_secret.encode(), text.encode(), hashlib.sha256).hexdigest()

        return {
            'ACCESS-KEY': self._access_key,
            'ACCESS-TIMESTAMP': access_timestamp,
            'ACCESS-SIGN': access_sign,
            'Content-Type': 'application/json',
        }

    def _request(
            self, http_method: str, request_path: str,
            request_body: Optional[str] = None, request_params: Optional[Dict] = None,
            auth: bool = True,
    ) -> requests.Response:

        path = f'/{self.API_VERSION}/{request_path}'
        arguments = {'url': f'{self.URL_BASE}{path}'}
        if request_body is not None:
            arguments['data'] = request_body
        if request_params is not None:
            arguments['params'] = request_params
        if auth:
            arguments['headers'] = self._get_auth_header(
                http_method, path,
                request_body or '', request_params or {},
            )

        response = getattr(requests, http_method.lower())(**arguments)
        try:
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(e.response.text)
            raise
        return response

    def get_balance(self) -> List[Balance]:
        response = self._request('GET', 'me/getbalance')
        return [Balance(**r) for r in response.json()]

    def get_positions(self) -> List[Position]:
        response = self._request('GET', 'me/getpositions', request_params={'product_code': ProductCode.FX_BTC_JPY.name})
        return [Position.from_dict(r) for r in response.json()]

    def send_child_order(self, params: ChildOrderRequest) -> ChildOrderResponse:
        response = self._request('POST', 'me/sendchildorder', request_body=params.to_json())
        return ChildOrderResponse(**response.json())


class BitFlyerRealTime:
    ENDPOINT = 'wss://ws.lightstream.bitflyer.com/json-rpc'

    def __init__(self) -> None:
        websocket.enableTrace(False)
        self._ws_app = websocket.WebSocketApp(
            self.ENDPOINT,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )

        self._thread: Optional[Thread] = None
        self._to_stop = True
        self._message_handler_of: Dict[str, Callable] = {}

    def stop(self) -> None:
        self._to_stop = True
        self._ws_app.close()

    def start(self) -> None:
        self._to_stop = False
        logger.info('websocket server is now starting')

        def run(ws: WebSocketApp) -> None:
            while True:
                if self._to_stop:
                    break

                ws.run_forever(ping_interval=30, ping_timeout=10)
                time.sleep(1)

        t = Thread(target=run, args=(self._ws_app,))
        t.start()
        self._thread = t

        logger.info('websocket server has started')

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def subscribe(self, channel: Channel, product_code: ProductCode, handler: Callable) -> None:
        channel_name = f'{channel.name}_{product_code.name}'
        self._message_handler_of[channel_name] = handler
        try:
            self._subscribe(channel_name)
        except WebSocketConnectionClosedException:
            pass

    def _subscribe(self, channel: str) -> None:
        self._ws_app.send(json.dumps({
            'method': 'subscribe',
            'params': {'channel': channel},
        }))

    def _on_message(self, _: WebSocketApp, json_str: str) -> None:
        msg = json.loads(json_str)
        params = msg['params']
        channel: str = params['channel']
        message = params['message']
        handler = self._message_handler_of[channel]

        if channel.startswith(PublicChannel.lightning_ticker.name):
            handler(Ticker.from_dict(message))

    def _on_error(self, _: WebSocketApp, error) -> None:
        logger.error(error)

    def _on_close(self, ws: WebSocketApp, close_status_code, close_msg) -> None:
        logger.info('connection closed')

    def _on_open(self, _: WebSocketApp):
        for c in self._message_handler_of.keys():
            logger.info(f'`{c}` has been subscribed')
            self._subscribe(c)
