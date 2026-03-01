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

    # PayFast marketplace URLs
    payfast_marketplace_return_url: str = "https://www.elitetcg.co.za/marketplace/payment/success"
    payfast_marketplace_cancel_url: str = "https://www.elitetcg.co.za/marketplace/payment/cancel"
    payfast_marketplace_notify_url: str = "https://cgpf.elitetcg.co.za/api/v1/marketplace/payfast/notify"
    payfast_promo_notify_url: str = "https://cgpf.elitetcg.co.za/api/v1/promotions/notify"

    # Courier Guy
    courier_guy_api_key: str
    courier_guy_account_number: str = ""
    courier_guy_webhook_secret: str = ""

    # App
    frontend_url: str = "https://www.elitetcg.co.za"
    app_env: str = "development"
    admin_api_key: str = ""

    # Seller address (Courier Guy pickup)
    seller_company_name: str = "Elite TCG"
    seller_address_line1: str = ""
    seller_city: str = "Vanderbijlpark"
    seller_province: str = "Gauteng"
    seller_postal_code: str = ""
    seller_phone: str = ""
    seller_email: str = ""

    # ZeptoMail (transactional emails)
    zeptomail_api_key: str = ""
    zeptomail_from_email: str = "admin@elitetcg.co.za"
    zeptomail_from_name: str = "Elite TCG"

    # Pokemon TCG API
    pokemon_tcg_api_key: str = ""

    # Exchange rate fallback
    usd_to_zar: float = 17.80

    # Supabase Auth
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    # Google Cloud Vision (card scanning)
    google_cloud_vision_api_key: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
