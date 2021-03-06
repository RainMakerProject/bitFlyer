from typing import Callable, Dict, Optional

import json
import time
import logging

from threading import Thread

import websocket
from websocket import WebSocketApp, WebSocketConnectionClosedException

from bitflyer.enumerations import ProductCode, Channel, PublicChannel
from bitflyer.responses import Ticker

logger = logging.getLogger(__name__)


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

    def _on_close(self, _: WebSocketApp) -> None:
        logger.info('connection closed')

    def _on_open(self, _: WebSocketApp):
        for c in self._message_handler_of.keys():
            logger.info(f'`{c}` has been subscribed')
            self._subscribe(c)
