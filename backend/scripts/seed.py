"""Seed script to create demo accounts.

Run from the backend directory:
    python -m scripts.seed
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.infrastructure.security import hash_password
from app.models.user import User
from app.schemas.enums import UserRole


async def seed():
    """Create demo admin and staff accounts."""
    from app.infrastructure.database import async_session_factory, engine

    async with async_session_factory() as session:
        from sqlalchemy import select

        # Check if admin already exists
        result = await session.execute(
            select(User).where(User.email == "admin@vendora.com")
        )
        if result.scalar_one_or_none():
            print("Demo accounts already exist. Skipping.")
            return

        # Create admin account
        admin = User(
            full_name="Admin Demo",
            email="admin@vendora.com",
            password_hash=hash_password("admin123"),
            role=UserRole.admin,
            is_active=True,
        )

        # Create staff account
        staff = User(
            full_name="Staff Demo",
            email="staff@vendora.com",
            password_hash=hash_password("staff123"),
            role=UserRole.staff,
            is_active=True,
        )

        session.add(admin)
        session.add(staff)
        await session.commit()

        print("✅ Demo accounts created:")
        print("   Admin: admin@vendora.com / admin123")
        print("   Staff: staff@vendora.com / staff123")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
