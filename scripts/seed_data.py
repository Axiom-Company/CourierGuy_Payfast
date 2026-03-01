"""
Seed sample products for testing.
Run: python -m scripts.seed_data
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import AsyncSessionLocal
from app.domain.models.product import Product
from app.domain.models.user import Customer
from app.domain.enums import ProductType, SealedCategory, CardCondition
from sqlalchemy import select


SEALED_PRODUCTS = [
    {
        "name": "Scarlet & Violet - Stellar Crown Booster Box",
        "product_type": ProductType.SEALED,
        "sealed_category": SealedCategory.BOOSTER_BOX,
        "set_name": "Stellar Crown",
        "sell_price_zar": 2499.00,
        "cost_price_zar": 1800.00,
        "margin_percent": 38.8,
        "quantity": 5,
        "weight_grams": 800,
    },
    {
        "name": "Scarlet & Violet - Prismatic Evolutions ETB",
        "product_type": ProductType.SEALED,
        "sealed_category": SealedCategory.ETB,
        "set_name": "Prismatic Evolutions",
        "sell_price_zar": 1299.00,
        "cost_price_zar": 900.00,
        "margin_percent": 44.3,
        "quantity": 10,
        "weight_grams": 600,
    },
    {
        "name": "Scarlet & Violet - Surging Sparks Booster Pack",
        "product_type": ProductType.SEALED,
        "sealed_category": SealedCategory.BOOSTER_PACK,
        "set_name": "Surging Sparks",
        "sell_price_zar": 89.00,
        "cost_price_zar": 55.00,
        "margin_percent": 61.8,
        "quantity": 50,
        "weight_grams": 30,
    },
]

SINGLE_CARDS = [
    {
        "name": "Charizard ex",
        "product_type": ProductType.SINGLE,
        "tcg_id": "sv3pt5-6",
        "card_number": "006/165",
        "set_id": "sv3pt5",
        "set_name": "151",
        "rarity": "Double Rare",
        "card_type": "Fire",
        "condition": CardCondition.NEAR_MINT,
        "condition_multiplier": 0.95,
        "sell_price_zar": 450.00,
        "market_price_usd": 15.00,
        "market_price_zar": 277.50,
        "margin_percent": 30.0,
        "quantity": 2,
        "weight_grams": 100,
    },
    {
        "name": "Pikachu ex",
        "product_type": ProductType.SINGLE,
        "tcg_id": "sv1-55",
        "card_number": "055/198",
        "set_id": "sv1",
        "set_name": "Scarlet & Violet",
        "rarity": "Double Rare",
        "card_type": "Lightning",
        "condition": CardCondition.MINT,
        "condition_multiplier": 1.00,
        "sell_price_zar": 250.00,
        "market_price_usd": 8.00,
        "market_price_zar": 148.00,
        "margin_percent": 30.0,
        "quantity": 3,
        "weight_grams": 100,
    },
    {
        "name": "Mewtwo ex",
        "product_type": ProductType.SINGLE,
        "tcg_id": "sv3pt5-150",
        "card_number": "150/165",
        "set_id": "sv3pt5",
        "set_name": "151",
        "rarity": "Illustration Rare",
        "card_type": "Psychic",
        "condition": CardCondition.LIGHTLY_PLAYED,
        "condition_multiplier": 0.85,
        "sell_price_zar": 1200.00,
        "market_price_usd": 45.00,
        "market_price_zar": 832.50,
        "margin_percent": 30.0,
        "quantity": 1,
        "weight_grams": 100,
    },
]


async def seed():
    async with AsyncSessionLocal() as session:
        # Find a seller to assign products to
        result = await session.execute(
            select(Customer).where(Customer.is_seller == True).limit(1)
        )
        seller = result.scalar_one_or_none()
        if not seller:
            print("No seller found. Run create_seller.py first.")
            return

        print(f"Using seller: {seller.email}")

        for data in SEALED_PRODUCTS + SINGLE_CARDS:
            product = Product(listed_by=seller.id, **data)
            session.add(product)
            print(f"  Added: {data['name']}")

        await session.commit()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
