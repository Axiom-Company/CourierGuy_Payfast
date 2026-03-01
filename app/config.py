from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str
    database_url_sync: str = ""

    # PayFast
    payfast_merchant_id: str
    payfast_merchant_key: str
    payfast_passphrase: str = ""
    payfast_sandbox: bool = True
    payfast_return_url: str
    payfast_cancel_url: str
    payfast_notify_url: str

    # Courier Guy
    courier_guy_api_key: str
    courier_guy_account_number: str = ""
    courier_guy_webhook_secret: str = ""

    # App
    frontend_url: str = "https://www.elitetcg.co.za"
    app_env: str = "development"
    admin_api_key: str = ""

    # Seller address (Courier Guy pickup)
    seller_address_line1: str = ""
    seller_city: str = "Vanderbijlpark"
    seller_province: str = "Gauteng"
    seller_postal_code: str = ""
    seller_phone: str = ""
    seller_email: str = ""

    # SMTP (for order confirmation emails)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
