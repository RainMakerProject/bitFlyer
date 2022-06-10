from typing import Any, Dict, Optional

from dataclasses import dataclass
from datetime import datetime

from .enumerations import Side, ProductCode, State, HealthStatus


def get_datetime_from(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None

    if ts.endswith('Z'):
        ts = ts[:-1]
    _ts, _ms, *_ = ts.split('.') + [None]  # noqa
    ms = _ms[:6] if _ms else '0'
    timestamp_str = f'{_ts}.{ms}+00:00'
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
class Collateral:
    collateral: int
    open_position_pnl: int
    require_collateral: int
    keep_rate: float
    margin_call_amount: int
    margin_call_due_date: Optional[datetime]  # "2021-09-01T08:00:00"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Collateral':
        return cls(**{**data, **{'margin_call_due_date': get_datetime_from(data['margin_call_due_date'])}})


@dataclass(frozen=True)
class CollateralHistory:
    id: int
    currency_code: str
    change: int
    reason_code: str
    amount: int
    date: datetime

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CollateralHistory':
        return cls(**{**data, **{'date': get_datetime_from(data['date'])}})


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
