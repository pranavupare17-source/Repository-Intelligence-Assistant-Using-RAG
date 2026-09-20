"""
Order Orchestration and Fulfillment Module.
Coordinates user authentication, database persistence, and payment transactions.
"""
from typing import Dict, Any, Optional, List
import uuid

from .auth import TokenService, hash_password
from .database import DatabasePool, execute_query_with_retry
from .payment_gateway import StripeGateway, calculate_processing_fee


class BaseService:
    """
    Base service abstraction providing structured event auditing and telemetry.
    """
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.audit_log: List[Dict[str, Any]] = []

    def log_event(self, event_name: str, payload: Dict[str, Any]) -> None:
        """
        Records an internal operational audit entry.
        """
        entry = {
            "service": self.service_name,
            "event": event_name,
            "data": payload,
        }
        self.audit_log.append(entry)


class OrderService(BaseService):
    """
    Orchestrates e-commerce checkout pipelines, inventory holds, and gateway charges.
    """
    def __init__(
        self,
        db_pool: DatabasePool,
        token_service: TokenService,
        payment_gateway: StripeGateway,
    ):
        super().__init__(service_name="OrderService")
        self.db_pool = db_pool
        self.token_service = token_service
        self.payment_gateway = payment_gateway

    def validate_checkout(self, token: str, cart_items: List[Dict[str, Any]]) -> bool:
        """
        Verifies caller authorization token and confirms valid non-empty checkout payload.
        """
        user_context = self.token_service.verify_token(token)
        if not user_context:
            return False
        if not cart_items:
            return False
        return True

    def process_order(
        self,
        token: str,
        customer_id: str,
        amount_cents: int,
        cart_items: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Authorizes the user, charges customer instrument, and records order in the database.
        """
        items = cart_items or [{"sku": "default", "qty": 1}]
        if not self.validate_checkout(token, items):
            raise PermissionError("Unauthorized or invalid checkout payload")

        fee = calculate_processing_fee(amount_cents)
        charge_receipt = self.payment_gateway.charge(
            amount_cents=amount_cents,
            currency="usd",
            customer_id=customer_id,
        )

        order_id = f"ord_{uuid.uuid4().hex[:12]}"
        query = f"INSERT INTO orders (id, customer_id, amount, fee) VALUES ('{order_id}', '{customer_id}', {amount_cents}, {fee})"
        execute_query_with_retry(self.db_pool, query)

        self.log_event("order_completed", {"order_id": order_id, "amount": amount_cents})
        return {
            "order_id": order_id,
            "status": "confirmed",
            "charge": charge_receipt,
            "processing_fee": fee,
        }

    def cancel_order(self, order_id: str, transaction_id: str) -> Dict[str, Any]:
        """
        Issues refund through payment gateway and updates database order record to cancelled.
        """
        refund_res = self.payment_gateway.refund(transaction_id, reason="order_cancelled")
        query = f"UPDATE orders SET status = 'cancelled' WHERE id = '{order_id}'"
        execute_query_with_retry(self.db_pool, query)
        self.log_event("order_cancelled", {"order_id": order_id, "refund": refund_res})
        return refund_res


def format_order_summary(order_id: str, total_cents: int) -> str:
    """
    Formats customer-facing order summary receipt string.
    """
    total_dollars = total_cents / 100.0
    return f"Order {order_id}: Total ${total_dollars:.2f} USD"
