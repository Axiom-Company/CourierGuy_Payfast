"""
PayFast payment gateway.
Docs: https://developers.payfast.co.za/docs

Flow:
1. Generate signed payment data -> frontend POSTs a form to PayFast
2. Customer pays on PayFast's hosted page
3. PayFast sends ITN (webhook) to /api/v1/checkout/payfast/notify
4. We verify signature + server validation -> update order
"""
import hashlib
import urllib.parse
import httpx
from app.config import get_settings


class PayFastClient:
    SANDBOX_PROCESS = "https://sandbox.payfast.co.za/eng/process"
    PRODUCTION_PROCESS = "https://www.payfast.co.za/eng/process"
    SANDBOX_VALIDATE = "https://sandbox.payfast.co.za/eng/query/validate"
    PRODUCTION_VALIDATE = "https://www.payfast.co.za/eng/query/validate"

    def __init__(self):
        settings = get_settings()
        self.merchant_id = settings.payfast_merchant_id
        self.merchant_key = settings.payfast_merchant_key
        self.passphrase = settings.payfast_passphrase
        self.is_sandbox = settings.payfast_sandbox
        self.return_url = settings.payfast_return_url
        self.cancel_url = settings.payfast_cancel_url
        self.notify_url = settings.payfast_notify_url

    @property
    def process_url(self) -> str:
        return self.SANDBOX_PROCESS if self.is_sandbox else self.PRODUCTION_PROCESS

    @property
    def validate_url(self) -> str:
        return self.SANDBOX_VALIDATE if self.is_sandbox else self.PRODUCTION_VALIDATE

    def generate_payment_data(
        self, order_number: str, total_zar: float, item_name: str,
        email: str, name_first: str = "", name_last: str = "",
    ) -> dict:
        """Build signed payment form data. Frontend submits this as a POST form to PayFast."""
        data = {
            "merchant_id": self.merchant_id,
            "merchant_key": self.merchant_key,
            "return_url": f"{self.return_url}?order={order_number}",
            "cancel_url": self.cancel_url,
            "notify_url": self.notify_url,
            "name_first": name_first,
            "name_last": name_last,
            "email_address": email,
            "m_payment_id": order_number,
            "amount": f"{total_zar:.2f}",
            "item_name": item_name[:100],
        }
        data = {k: v for k, v in data.items() if v}
        data["signature"] = self._sign(data)
        return data

    def _sign(self, data: dict) -> str:
        param_str = "&".join(f"{k}={urllib.parse.quote_plus(str(v))}" for k, v in data.items() if v and k != "signature")
        if self.passphrase:
            param_str += f"&passphrase={urllib.parse.quote_plus(self.passphrase)}"
        return hashlib.md5(param_str.encode()).hexdigest()

    def verify_itn_signature(self, posted: dict) -> bool:
        received = posted.get("signature", "")
        clean = {k: v for k, v in posted.items() if k != "signature" and v}
        param_str = "&".join(f"{k}={urllib.parse.quote_plus(str(v))}" for k, v in clean.items())
        if self.passphrase:
            param_str += f"&passphrase={urllib.parse.quote_plus(self.passphrase)}"
        return hashlib.md5(param_str.encode()).hexdigest() == received

    def generate_marketplace_payment_data(
        self, order_id: str, order_number: str, total_zar: float, item_name: str,
        email: str, name_first: str = "", name_last: str = "",
        notify_url: str = "", return_url: str = "", cancel_url: str = "",
        custom_str1: str = "", custom_str2: str = "",
        custom_str3: str = "", custom_str4: str = "",
        custom_int1: int | None = None,
    ) -> dict:
        """Build signed payment data for marketplace transactions.

        Uses order_id (UUID) as m_payment_id and supports custom fields
        for order_number, listing_id, seller info, etc.
        """
        data = {
            "merchant_id": self.merchant_id,
            "merchant_key": self.merchant_key,
            "return_url": return_url or f"{self.return_url}?order={order_number}",
            "cancel_url": cancel_url or self.cancel_url,
            "notify_url": notify_url or self.notify_url,
            "name_first": name_first,
            "name_last": name_last,
            "email_address": email,
            "m_payment_id": order_id,
            "amount": f"{total_zar:.2f}",
            "item_name": item_name[:100],
            "custom_str1": custom_str1,
            "custom_str2": custom_str2,
            "custom_str3": custom_str3,
            "custom_str4": custom_str4,
        }
        if custom_int1 is not None:
            data["custom_int1"] = str(custom_int1)
        data = {k: v for k, v in data.items() if v}
        data["signature"] = self._sign(data)
        return data

    async def validate_itn_server(self, posted: dict) -> bool:
        """Server-to-server validation -- confirm ITN is legit."""
        param_str = "&".join(f"{k}={urllib.parse.quote_plus(str(v))}" for k, v in posted.items())
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.validate_url, data=param_str,
                                     headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30.0)
            return resp.text.strip() == "VALID"
