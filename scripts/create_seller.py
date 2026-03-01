"""
Promote existing Supabase Auth users to seller.
The user must already exist (signed up via Supabase Auth).

Run: python -m scripts.create_seller
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import AsyncSessionLocal
from app.domain.models.user import Customer
from sqlalchemy import select, update


SELLER_EMAILS = [
    "brandon@pokemoncardssa.co.za",
    "ruben@pokemoncardssa.co.za",
]


async def promote_sellers():
    async with AsyncSessionLocal() as session:
        for email in SELLER_EMAILS:
            result = await session.execute(
                select(Customer).where(Customer.email == email)
            )
            customer = result.scalar_one_or_none()
            if not customer:
                print(f"Customer not found (user must sign up first): {email}")
                continue

            if customer.is_seller:
                print(f"Already a seller: {email}")
                continue

            await session.execute(
                update(Customer).where(Customer.id == customer.id).values(is_seller=True)
            )
            print(f"Promoted to seller: {email}")

        await session.commit()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(promote_sellers())
