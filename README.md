# URBAN-SCENERY-VENTURES

A high-performance, AI-powered e-commerce backend for electronics, built with **FastAPI**, **SQLAlchemy 2.0**, and **Pydantic**.

---

## Features

- **Electronics Product Catalog**: Search, filter by price, browse inventory status, and manage stock quantities.
- **Order Management**: Real-time stock validation, automated price computation, and multi-step order lifecycle (Pending, Approved, Shipped, Delivered).
- **Payment Processing**: Payment records and routes exist, but no verified payment gateway is configured. The payment endpoint returns `501 Not Implemented` and does not mark orders as paid until a provider integration and verified callback are implemented.
- **AI Electronics Assistant**:
  - Semantic smart search with keyword expansion for electronics (smartphones, laptops, monitors, gaming accessories, audio gear).
  - Budget-aware recommendation engine tailored to user requirements.
- **Research-scope AI modules**:
  - Business intelligence and decision support for administrators.
  - Product discovery and catalogue-grounded recommendations.
  - AI Image Studio with a prompt endpoint and optional Google Gen AI image rendering.
  - Marketing content generation with human review before publication.
  - Customer shopping assistant, including an inbound WhatsApp webhook.
  - Growth optimization recommendations grounded in available business records.
- **External platform adapters**: WhatsApp Cloud API, Facebook Page publishing, Instagram image publishing, TikTok video publishing, and approved multi-platform campaign publishing. Credentials and provider permissions must be configured separately; see [Platform Integration Setup](docs/PLATFORM_INTEGRATIONS.md).
- **Authentication & Role-Based Authorization**:
  - Secure PBKDF2-HMAC-SHA256 password hashing.
  - URL-safe JWT access tokens.
  - Role hierarchy: `ADMIN`, `CUSTOMER`, and `GUEST`.

---

## Project Structure

```
URBAN-SCENERY-VENTURES/
│
├── core/
│   ├── config.py             # Settings, JWT config, CORS
│   ├── database.py           # Database initialization and sessions
│   └── security.py           # Password hashing, JWT, auth dependencies
├── models/
│   ├── users_model.py        # User table (UUIDs, role, hashed_password)
│   ├── products_model.py     # Electronics product table (price, quantity, status)
│   ├── order_model.py        # Order table (linked to user and product)
│   ├── payment_model.py      # Payment table (1:1 with order)
│   ├── ai_model.py           # AI interaction logs
│   └── utils.py              # Timestamp mixin and system Enums
├── schemas/
│   ├── user_schema.py        # Pydantic schemas for authentication and users
│   ├── product_schema.py     # Pydantic schemas for electronics products
│   ├── order_schema.py       # Pydantic schemas for purchase orders
│   ├── payment_schema.py     # Pydantic schemas for payment processing
│   └── ai_schema.py          # Pydantic schemas for AI recommendations
├── routers/
│   ├── auth.py               # /api/v1/auth (Register, Login, /me)
│   ├── users.py              # /api/v1/users (Admin CRUD, profile updates)
│   ├── products.py           # /api/v1/products (Electronics catalog and stock)
│   ├── orders.py             # /api/v1/orders (Order placement, inventory reservation)
│   ├── payments.py           # /api/v1/payments (Payment processing & receipts)
│   └── ai.py                 # /api/v1/ai (AI recommendation and smart search)
├── services/
│   ├── user_service.py       # User business logic
│   ├── product_service.py    # Product business logic and inventory checks
│   ├── order_service.py      # Order calculation and stock updates
│   ├── payment_service.py    # Payment verification and order settlement
│   ├── ai_service.py         # AI scoring and semantic search logic
│   ├── ai_agents.py          # Database-grounded agent orchestration
│   ├── image_generation.py   # Google Gen AI image rendering
│   ├── platform_integrations.py # WhatsApp, Meta, and TikTok API adapters
│   └── whatsapp_webhook.py   # Signature verification and duplicate-event handling
├── settings.py               # Database engine & get_db dependency
├── main.py                   # FastAPI application entry point
├── seed_data.py              # Seeds initial admin, customer, and sample electronics
├── prompts/                  # Editable Markdown instructions for all agents
├── tests/                    # Automated API, service, and integration tests
├── docs/PLATFORM_INTEGRATIONS.md
└── test_backend.py           # Legacy test runner
```

---

## Getting Started

### 1. Activate Environment & Install Dependencies

```bash
# Using Python 3.13 virtual environment:
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Variables

Copy `.env.example` to `.env` and configure the required local settings:
```env
DATABASE_URL=sqlite:///./urban_ventures.db
SECRET_KEY=your-secure-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

### 3. Seed Sample Electronics & Admin Account

```bash
python seed_data.py
```
This sets up:
- **Admin**: `admin@urbanventures.com` / `admin123`
- **Customer**: `customer@example.com` / `customer123`
- Pre-populated electronics: MacBook Pro M3, Sony WH-1000XM5, Galaxy S24 Ultra, Dell 4K Monitor, Anker Power Bank, PlayStation 5.

### 4. Run the Development Server

```bash
uvicorn main:app --reload --port 8000
```

Open your browser to:
- **Interactive OpenAPI Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative ReDoc UI**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Root Health & Endpoint Index**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

### 5. Run the Test Suite

```bash
python test_backend.py
```
