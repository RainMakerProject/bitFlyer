from typing import Literal, Optional

import json
from dataclasses import dataclass, asdict

from .enumerations import ProductCode


@dataclass(frozen=True)
class ChildOrderRequest:
    product_code: ProductCode
    child_order_type: Literal['LIMIT', 'MARKET']
    side: Literal['BUY', 'SELL']
    size: float
    price: Optional[int] = None
    minute_to_expire: int = 30 * 24 * 60
    time_in_force: Literal['GTC', 'IOC', 'FOK'] = 'GTC'

    def to_json(self) -> str:
        d = asdict(self)
        d['product_code'] = self.product_code.name
        if self.price is None:
            del d['price']

        return json.dumps(d)
