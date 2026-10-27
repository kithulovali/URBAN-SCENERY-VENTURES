"""Seed database with sample electronics products and initial admin user."""
from decimal import Decimal
from settings import sessionlocal, engine, Model
from models.users_model import User
from models.products_model import Product
from models.utils import UserRole, ProductStatus
from services.lookup_service import get_lookup
from core.security import hash_password


def seed():
    # Ensure tables exist
    Model.metadata.create_all(bind=engine)
    db = sessionlocal()

    try:
        # 1. Seed Admin User
        admin_email = "admin@urbanventures.com"
        admin = db.query(User).filter(User.email == admin_email).first()
        if not admin:
            admin = User(
                name="Admin Manager",
                email=admin_email,
                hashed_password=hash_password("admin123"),
                role=get_lookup(db, UserRole, "ADMIN"),
                contact="+250788000001",
            )
            db.add(admin)
            print("Created default admin user: admin@urbanventures.com / admin123")

        # 2. Seed Customer User
        customer_email = "customer@example.com"
        customer = db.query(User).filter(User.email == customer_email).first()
        if not customer:
            customer = User(
                name="John Techie",
                email=customer_email,
                hashed_password=hash_password("customer123"),
                role=get_lookup(db, UserRole, "CUSTOMER"),
                contact="+250788000002",
            )
            db.add(customer)
            print("Created default customer user: customer@example.com / customer123")

        # 3. Seed Sample Electronics Catalog
        sample_electronics = [
            {
                "name": "Apple MacBook Pro 14 M3 Pro",
                "price": Decimal("1999.00"),
                "description": "14-inch Liquid Retina XDR display, 18GB Unified Memory, 512GB SSD, Space Black. Designed for high performance developers and creators.",
                "banner_image": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8",
                "quantity": 15,
                "status": ProductStatus.Available.value,
            },
            {
                "name": "Sony WH-1000XM5 Wireless Headphones",
                "price": Decimal("399.99"),
                "description": "Industry-leading noise canceling Bluetooth headphones with Auto NC Optimizer, crystal clear hands-free calling, and 30-hour battery life.",
                "banner_image": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e",
                "quantity": 30,
                "status": ProductStatus.Available.value,
            },
            {
                "name": "Samsung Galaxy S24 Ultra",
                "price": Decimal("1299.99"),
                "description": "Titanium Gray, 256GB, Galaxy AI powered smartphone with 200MP camera, Snapdragon 8 Gen 3, and built-in S Pen.",
                "banner_image": "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c",
                "quantity": 25,
                "status": ProductStatus.Available.value,
            },
            {
                "name": "Dell UltraSharp 27 4K USB-C Monitor (U2723QE)",
                "price": Decimal("579.50"),
                "description": "IPS Black technology with 2000:1 contrast ratio, 98% DCI-P3 color gamut, 4K resolution, and 90W USB-C power delivery hub.",
                "banner_image": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf",
                "quantity": 10,
                "status": ProductStatus.Available.value,
            },
            {
                "name": "Anker 737 Power Bank (PowerCore 24K)",
                "price": Decimal("149.99"),
                "description": "24,000mAh 3-port portable charger with 140W fast output, smart digital display, compatible with laptops, phones, and tablets.",
                "banner_image": "https://images.unsplash.com/photo-1609592424364-c78d53b27670",
                "quantity": 50,
                "status": ProductStatus.Available.value,
            },
            {
                "name": "Sony PlayStation 5 Slim Console",
                "price": Decimal("499.00"),
                "description": "Next-gen gaming console with 1TB SSD, ultra-high speed SSD, ray tracing, 4K-TV gaming, and DualSense wireless controller.",
                "banner_image": "https://images.unsplash.com/photo-1606813907291-d86efa9b94db",
                "quantity": 8,
                "status": ProductStatus.Available.value,
            },
        ]

        for item in sample_electronics:
            existing = db.query(Product).filter(Product.name == item["name"]).first()
            if not existing:
                product_data = dict(item)
                status_name = product_data.pop("status", "AVAILABLE")
                product_data["product_status_record"] = get_lookup(db, ProductStatus, status_name)
                prod = Product(**product_data)
                db.add(prod)
                print(f"Added electronics product: {item['name']}")

        db.commit()
        print("Database seeding completed successfully!")
    except Exception as e:
        db.rollback()
        print(f"Seeding failed: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
