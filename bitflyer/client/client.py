import dataclasses
from typing import Dict, List, Optional

import hmac
import hashlib
import requests
import urllib
import time
import logging

from bitflyer.enumerations import ProductCode
from bitflyer.requests import ChildOrderRequest, PaginationParams
from bitflyer.responses import Ticker, Balance, Collateral, CollateralHistory, Position, ChildOrderResponse, Health

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

    def get_health(self, product_code: ProductCode) -> Health:
        response = self._request('GET', 'gethealth', request_params={'product_code': product_code.name}, auth=False)
        return Health.from_dict(response.json())

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

    def get_collateral(self) -> Collateral:
        response = self._request('GET', 'me/getcollateral')
        return Collateral.from_dict(response.json())

    def get_collateral_history(self, pagination_params: PaginationParams = PaginationParams()) -> List[CollateralHistory]:
        response = self._request(
            'GET', 'me/getcollateralhistory',
            request_params={k: v for k, v in dataclasses.asdict(pagination_params).items() if v is not None},
        )
        return [CollateralHistory.from_dict(r) for r in response.json()]

    def get_positions(self) -> List[Position]:
        response = self._request('GET', 'me/getpositions', request_params={'product_code': ProductCode.FX_BTC_JPY.name})
        return [Position.from_dict(r) for r in response.json()]

    def send_child_order(self, params: ChildOrderRequest) -> ChildOrderResponse:
        response = self._request('POST', 'me/sendchildorder', request_body=params.to_json())
        return ChildOrderResponse(**response.json())
