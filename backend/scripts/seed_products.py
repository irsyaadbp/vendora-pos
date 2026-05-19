"""Seed script to create demo categories and products.

Run from the backend directory:
    python -m scripts.seed_products
"""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.infrastructure.database import async_session_factory, engine
from app.models.category import Category
from app.models.product import Product
from sqlalchemy import select


CATEGORIES = [
    {"name": "Makanan", "description": "Produk makanan dan snack"},
    {"name": "Minuman", "description": "Minuman dingin dan panas"},
    {"name": "Rokok", "description": "Rokok dan tembakau"},
    {"name": "Kebutuhan Rumah", "description": "Sabun, deterjen, dll"},
    {"name": "Alat Tulis", "description": "Pena, buku, kertas"},
]

PRODUCTS = [
    # Makanan
    {"name": "Indomie Goreng", "sku": "MKN-001", "barcode": "8996001010101", "price": Decimal("3500"), "stock": 200, "category": "Makanan"},
    {"name": "Indomie Kuah Soto", "sku": "MKN-002", "barcode": "8996001010102", "price": Decimal("3500"), "stock": 150, "category": "Makanan"},
    {"name": "Chitato Original 68g", "sku": "MKN-003", "barcode": "8996001010103", "price": Decimal("12000"), "stock": 80, "category": "Makanan"},
    {"name": "Oreo Vanilla 137g", "sku": "MKN-004", "barcode": "8996001010104", "price": Decimal("10500"), "stock": 60, "category": "Makanan"},
    {"name": "Roti Tawar Sari Roti", "sku": "MKN-005", "barcode": "8996001010105", "price": Decimal("15000"), "stock": 30, "category": "Makanan"},
    {"name": "Tango Wafer Coklat", "sku": "MKN-006", "barcode": "8996001010106", "price": Decimal("5000"), "stock": 100, "category": "Makanan"},
    {"name": "Good Day Cappuccino 250ml", "sku": "MKN-007", "barcode": "8996001010107", "price": Decimal("7000"), "stock": 5, "category": "Makanan"},
    # Minuman
    {"name": "Aqua 600ml", "sku": "MNM-001", "barcode": "8996001020101", "price": Decimal("4000"), "stock": 300, "category": "Minuman"},
    {"name": "Teh Botol Sosro 450ml", "sku": "MNM-002", "barcode": "8996001020102", "price": Decimal("5000"), "stock": 120, "category": "Minuman"},
    {"name": "Coca Cola 390ml", "sku": "MNM-003", "barcode": "8996001020103", "price": Decimal("7500"), "stock": 90, "category": "Minuman"},
    {"name": "Kopi ABC Susu 250ml", "sku": "MNM-004", "barcode": "8996001020104", "price": Decimal("5500"), "stock": 70, "category": "Minuman"},
    {"name": "Ultra Milk Coklat 250ml", "sku": "MNM-005", "barcode": "8996001020105", "price": Decimal("6000"), "stock": 50, "category": "Minuman"},
    {"name": "Sprite 390ml", "sku": "MNM-006", "barcode": "8996001020106", "price": Decimal("7500"), "stock": 8, "category": "Minuman"},
    # Rokok
    {"name": "Gudang Garam Surya 16", "sku": "RKK-001", "barcode": "8996001030101", "price": Decimal("28000"), "stock": 50, "category": "Rokok"},
    {"name": "Sampoerna Mild 16", "sku": "RKK-002", "barcode": "8996001030102", "price": Decimal("30000"), "stock": 40, "category": "Rokok"},
    {"name": "Djarum Super 12", "sku": "RKK-003", "barcode": "8996001030103", "price": Decimal("22000"), "stock": 35, "category": "Rokok"},
    # Kebutuhan Rumah
    {"name": "Rinso Anti Noda 800g", "sku": "RMH-001", "barcode": "8996001040101", "price": Decimal("18000"), "stock": 25, "category": "Kebutuhan Rumah"},
    {"name": "Sunlight Jeruk 800ml", "sku": "RMH-002", "barcode": "8996001040102", "price": Decimal("12000"), "stock": 30, "category": "Kebutuhan Rumah"},
    {"name": "Molto Pewangi 800ml", "sku": "RMH-003", "barcode": "8996001040103", "price": Decimal("15000"), "stock": 3, "category": "Kebutuhan Rumah"},
    {"name": "Baygon Aerosol 600ml", "sku": "RMH-004", "barcode": "8996001040104", "price": Decimal("45000"), "stock": 15, "category": "Kebutuhan Rumah"},
    # Alat Tulis
    {"name": "Pulpen Pilot G2", "sku": "ATK-001", "barcode": "8996001050101", "price": Decimal("15000"), "stock": 40, "category": "Alat Tulis"},
    {"name": "Buku Tulis Sidu 58 Lembar", "sku": "ATK-002", "barcode": "8996001050102", "price": Decimal("5000"), "stock": 60, "category": "Alat Tulis"},
    {"name": "Penghapus Staedtler", "sku": "ATK-003", "barcode": "8996001050103", "price": Decimal("3000"), "stock": 2, "category": "Alat Tulis"},
]


async def seed():
    async with async_session_factory() as session:
        # Seed categories
        category_map: dict[str, Category] = {}
        for cat_data in CATEGORIES:
            stmt = select(Category).where(Category.name == cat_data["name"])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                category_map[cat_data["name"]] = existing
                print(f"  ✓ Category '{cat_data['name']}' already exists")
            else:
                category = Category(name=cat_data["name"], description=cat_data["description"])
                session.add(category)
                await session.flush()
                await session.refresh(category)
                category_map[cat_data["name"]] = category
                print(f"  + Created category '{cat_data['name']}'")

        # Seed products
        for prod_data in PRODUCTS:
            stmt = select(Product).where(Product.sku == prod_data["sku"])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                print(f"  ✓ Product '{prod_data['name']}' already exists")
                continue

            category = category_map.get(prod_data["category"])
            product = Product(
                name=prod_data["name"],
                sku=prod_data["sku"],
                barcode=prod_data["barcode"],
                price=prod_data["price"],
                stock=prod_data["stock"],
                category_id=category.id if category else None,
            )
            session.add(product)
            print(f"  + Created product '{prod_data['name']}' (stock: {prod_data['stock']})")

        await session.commit()

    await engine.dispose()
    print(f"\nDone! {len(CATEGORIES)} categories, {len(PRODUCTS)} products seeded.")


if __name__ == "__main__":
    print("Seeding categories and products...\n")
    asyncio.run(seed())
