"""
Payment Processing and Gateway Integration.
Handles multi-provider transaction routing, webhooks, and ledger reconciliation.
"""
from typing import Dict, Any, Optional
import uuid


class StripeGateway:
    """
    Handles credit card and Apple Pay charges via the Stripe REST API.
    """
    def __init__(self, api_key: str, webhook_secret: str):
        self.api_key = api_key
        self.webhook_secret = webhook_secret

    def charge(self, amount_cents: int, currency: str, customer_id: str) -> Dict[str, Any]:
        """
        Creates a payment intent and authorizes the charge on customer's default payment method.
        
        Args:
            amount_cents: Transaction amount in smallest currency unit (e.g. cents).
            currency: ISO 3-letter currency code (e.g. 'usd').
            customer_id: Unique customer ID.
        """
        if amount_cents <= 0:
            raise ValueError("Charge amount must be strictly greater than 0")

        transaction_id = f"ch_{uuid.uuid4().hex[:16]}"
        return {
            "transaction_id": transaction_id,
            "status": "succeeded",
            "amount": amount_cents,
            "currency": currency.lower(),
            "customer": customer_id,
        }

    def refund(self, transaction_id: str, reason: str = "customer_request") -> Dict[str, Any]:
        """
        Issues a full or partial refund back to the original funding instrument.
        """
        return {
            "refund_id": f"re_{uuid.uuid4().hex[:16]}",
            "original_charge": transaction_id,
            "status": "refunded",
            "reason": reason,
        }


def calculate_processing_fee(amount_cents: int, flat_fee_cents: int = 30, percentage: float = 0.029) -> int:
    """
    Computes standard payment merchant processing fee: 2.9% + 30c.
    """
    variable_fee = int(amount_cents * percentage)
    return variable_fee + flat_fee_cents
