"""Payment provider adapterlari.

Hozir faqat mock provider mavjud. Real provider webhooki keyingi bosqichda shu interfeys
orqali ulanadi; karta ma’lumotlari bu loyihada saqlanmaydi.
"""
from dataclasses import dataclass
import time

@dataclass
class PaymentResult:
    ok: bool
    provider: str
    provider_payment_id: str
    status: str
    message: str = ""

class MockPaymentProvider:
    name = "mock"

    async def charge(self, order_id: int, amount: float) -> PaymentResult:
        return PaymentResult(True, self.name, f"mock_{order_id}_{int(time.time())}", "paid")

    async def refund(self, order_id: int, amount: float) -> PaymentResult:
        return PaymentResult(True, self.name, f"refund_{order_id}_{int(time.time())}", "refunded")


def get_provider(test_mode: bool = True):
    if test_mode:
        return MockPaymentProvider()
    raise RuntimeError("Real payment provider is not configured")
