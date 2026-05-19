# Vendora POS

A modern web-based Point of Sale system for small and medium businesses.

## Tech Stack

- **Frontend:** Next.js 15, TypeScript, TailwindCSS, Zustand, TanStack Query
- **Backend:** Python 3.12, FastAPI, SQLAlchemy, Alembic, Pydantic
- **Database:** Neon PostgreSQL
- **Auth:** JWT with refresh token rotation

## Prerequisites

- Python 3.12+
- Node.js 20+ (LTS)
- PostgreSQL database (Neon or local)

## Getting Started

### 1. Clone and set up environment variables

```bash
# Backend
cp backend/.env.example backend/.env
# Edit backend/.env with your database URL and JWT secret

# Frontend
cp frontend/.env.example frontend/.env.local
# Edit frontend/.env.local with the API URL
```

**Backend `.env` (required values):**

```env
DATABASE_URL=postgresql+asyncpg://user:password@host:port/dbname?sslmode=require
JWT_SECRET=your-strong-random-secret-key
```

**Frontend `.env.local`:**

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 2. Run the Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`. Health check: `http://localhost:8000/health`

### 3. Run the Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The app will be available at `http://localhost:3000`.

## Running with Docker

```bash
# Make sure .env files exist for both services
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000

## Running Tests

### Backend

```bash
cd backend
source .venv/bin/activate
python -m pytest tests/ --tb=short -q
```

### Frontend

```bash
cd frontend
npx vitest run
```

## Seeding Demo Data

After running migrations, seed demo accounts and products:

```bash
cd backend
source .venv/bin/activate

# Create demo user accounts (admin + staff)
python -m scripts.seed_demo

# Create demo categories and products
python -m scripts.seed_products
```

Demo accounts:
| Role | Email | Password |
|------|-------|----------|
| Admin | admin@vendora.com | admin123 |
| Staff | staff@vendora.com | staff123 |

## Project Structure

```
vendora-pos/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Route handlers
│   │   ├── core/            # Config, dependencies, exceptions
│   │   ├── domain/          # Interfaces (repository contracts)
│   │   ├── infrastructure/  # Database, security
│   │   ├── models/          # SQLAlchemy models
│   │   ├── repositories/    # Data access layer
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   └── services/        # Business logic
│   ├── alembic/             # Database migrations
│   └── tests/               # Unit + property-based tests
├── frontend/
│   ├── src/
│   │   ├── app/             # Next.js pages and layouts
│   │   ├── core/            # API client, stores, types
│   │   ├── features/        # Feature modules (auth, users, products, pos, inventory, dashboard)
│   │   ├── shared/          # Reusable UI components, hooks, utils
│   │   └── styles/          # Global styles
│   └── vitest.config.ts
├── docker-compose.yml
└── README.md
```

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/v1/auth/login | Public | Login |
| POST | /api/v1/auth/refresh | Cookie | Refresh token |
| POST | /api/v1/auth/logout | Cookie | Logout |
| GET | /api/v1/users | Admin | List users |
| POST | /api/v1/users | Admin | Create user |
| PUT | /api/v1/users/:id | Admin | Update user |
| GET | /api/v1/products | Auth | List products |
| GET | /api/v1/products/search | Auth | Search products |
| POST | /api/v1/products | Admin | Create product |
| GET | /api/v1/categories | Auth | List categories |
| POST | /api/v1/transactions | Auth | Create transaction |
| GET | /api/v1/transactions | Auth | List transactions (role-scoped) |
| POST | /api/v1/inventory/stock-in | Admin | Record stock in |
| POST | /api/v1/inventory/stock-out | Admin | Record stock out |
| GET | /api/v1/inventory/low-stock | Admin | Low stock products |
| GET | /api/v1/dashboard | Admin | Dashboard metrics |

## Default Roles

- **Admin** — Full access: users, products, inventory, dashboard, POS, transactions
- **Staff** — POS and own transaction history only
