"""Pydantic schemas for API request/response."""
from datetime import datetime

from pydantic import BaseModel


class ProductResponse(BaseModel):
    """Product catalog entry (derived from order_lines, one per stock_code)."""

    stock_code: str
    description: str
    price: float


class OrderLineResponse(BaseModel):
    """Single order line — one row of the Online Retail CSV."""

    id: int
    invoice: str
    stock_code: str
    description: str | None = None
    quantity: int
    invoice_date: datetime
    price: float
    customer_id: int | None = None
    country: str | None = None
    year: str | None = None
