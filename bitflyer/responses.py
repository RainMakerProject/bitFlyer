from typing import Any, Dict

from dataclasses import dataclass
from datetime import datetime

from .enumerations import Side, ProductCode, State, HealthStatus


def get_datetime_from(ts: str) -> datetime:
    if ts.endswith('Z'):
        ts = ts[:-1]
    if (sub := len(ts.split('.')[-1]) - 6) > 0:
        ts = ts[:-sub]
    timestamp_str = f'{ts}+00:00'
    try:
        return datetime.fromisoformat(timestamp_str)
    except ValueError:
        return datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S.%f%z')


@dataclass(frozen=True)
class Ticker:
    product_code: ProductCode
    state: State
    timestamp: datetime
    tick_id: int
    best_bid: float
    best_ask: float
    best_bid_size: float
    best_ask_size: float
    total_bid_depth: float
    total_ask_depth: float
    market_bid_size: float
    market_ask_size: float
    ltp: float
    volume: float
    volume_by_product: float

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Ticker':
        return Ticker(**{**data, **{
            'product_code': getattr(ProductCode, data['product_code']),
            'state': getattr(State, '_'.join(data['state'].split())),
            'timestamp': get_datetime_from(data['timestamp']),
        }})


@dataclass(frozen=True)
class Health:
    status: HealthStatus

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Health':
        return cls(getattr(HealthStatus, '_'.join(data['status'].split())))


@dataclass(frozen=True)
class Balance:
    currency_code: str
    amount: float
    available: float


@dataclass(frozen=True)
class Position:
    product_code: ProductCode
    side: Side
    price: float
    size: float
    commission: float
    swap_point_accumulate: float
    require_collateral: float
    open_date: datetime  # "2015-11-03T10:04:45.011",
    leverage: float
    pnl: float
    sfd: float

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Position':
        return cls(**{**data, **{
            'product_code': getattr(ProductCode, data['product_code']),
            'side': getattr(Side, data['side']),
            'open_date': get_datetime_from(data['open_date']),
        }})


@dataclass(frozen=True)
class ChildOrderResponse:
    child_order_acceptance_id: str
