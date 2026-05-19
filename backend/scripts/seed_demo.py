"""Seed script to create demo accounts for development/testing.

Run from the backend directory:
    python -m scripts.seed_demo

Creates two demo accounts:
    - Admin: admin@vendora.com / admin123
    - Staff: staff@vendora.com / staff123
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.infrastructure.database import async_session_factory, engine
from app.infrastructure.security import hash_password
from app.models.user import User
from app.schemas.enums import UserRole
from sqlalchemy import select


DEMO_USERS = [
    {
        "full_name": "Admin Demo",
        "email": "admin@vendora.com",
        "password": "admin123",
        "role": UserRole.admin,
    },
    {
        "full_name": "Staff Demo",
        "email": "staff@vendora.com",
        "password": "staff123",
        "role": UserRole.staff,
    },
]


async def seed():
    async with async_session_factory() as session:
        for user_data in DEMO_USERS:
            # Check if user already exists
            stmt = select(User).where(User.email == user_data["email"])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                print(f"  ✓ {user_data['email']} already exists (skipped)")
                continue

            user = User(
                full_name=user_data["full_name"],
                email=user_data["email"],
                password_hash=hash_password(user_data["password"]),
                role=user_data["role"],
            )
            session.add(user)
            print(f"  + Created {user_data['email']} ({user_data['role'].value})")

        await session.commit()

    await engine.dispose()
    print("\nDone! Demo accounts ready.")


if __name__ == "__main__":
    print("Seeding demo accounts...\n")
    asyncio.run(seed())
