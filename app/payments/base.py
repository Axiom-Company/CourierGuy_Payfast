"""
Abstract payment provider interface.

PayFast and Payflex (and future providers) implement this contract so the
checkout flow can work with any provider through a uniform API.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any


class PaymentProvider(ABC):
    """Strategy interface for payment providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier: 'payfast', 'payflex', etc."""
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """True if the provider is configured and healthy."""
        ...

    @abstractmethod
    async def create_checkout(self, order: Any) -> dict:
        """
        Prepare the checkout data for the given order.

        Returns a dict with at minimum:
            - provider: str
            - redirect_url or payment_data: depends on provider flow
        """
        ...

    @abstractmethod
    async def verify_payment(self, order_id: str) -> dict:
        """
        Verify payment status with the provider.

        Returns a dict with:
            - status: str (approved, declined, cancelled, pending, etc.)
            - amount: Decimal
            - provider_order_id: str
        """
        ...

    @abstractmethod
    async def refund(self, provider_order_id: str, amount: Decimal) -> dict:
        """Process a refund. Returns provider-specific refund details."""
        ...
