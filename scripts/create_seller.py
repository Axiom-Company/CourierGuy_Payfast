"""
Create seller accounts for Brandon and Ruben.
Run: python -m scripts.create_seller
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import AsyncSessionLocal
from app.domain.models.user import User
from app.domain.enums import UserRole
from app.utils.security import hash_password


SELLERS = [
    {
        "email": "brandon@pokemoncardssa.co.za",
        "full_name": "Brandon",
        "phone": "0821234567",
        "password": "seller123!",
    },
    {
        "email": "ruben@pokemoncardssa.co.za",
        "full_name": "Ruben",
        "phone": "0829876543",
        "password": "seller123!",
    },
]


async def create_sellers():
    async with AsyncSessionLocal() as session:
        for seller_data in SELLERS:
            from sqlalchemy import select
            result = await session.execute(
                select(User).where(User.email == seller_data["email"])
            )
            existing = result.scalar_one_or_none()
            if existing:
                print(f"Seller already exists: {seller_data['email']}")
                continue

            user = User(
                email=seller_data["email"],
                password_hash=hash_password(seller_data["password"]),
                full_name=seller_data["full_name"],
                phone=seller_data["phone"],
                role=UserRole.SELLER,
            )
            session.add(user)
            print(f"Created seller: {seller_data['email']}")

        await session.commit()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(create_sellers())
