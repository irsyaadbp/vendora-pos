# AGENTS.md

# Vendora POS

AI agent instructions and repository operating rules for Vendora POS.

This file defines how AI coding agents should understand, modify, and extend the codebase.

---

# Project Overview

Vendora is a modern Point of Sale (POS) platform built using:

- Frontend: Next.js 15 + TypeScript
- Backend: Python FastAPI
- Database: Neon PostgreSQL
- Authentication: JWT Authentication

Deployment target:

- VPS
- Docker-based deployment
- Dokploy orchestration

Architecture goals:

- Scalable
- Modular
- SOLID-compliant
- Testable
- Clean Architecture
- Maintainable long-term

---

# Core Stack

## Frontend

- Next.js 15
- TypeScript
- TailwindCSS
- Zustand
- TanStack Query
- React Hook Form
- Zod
- Axios

## Backend

- Python 3.12
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic
- Python-JOSE

## Infrastructure

- Neon PostgreSQL
- Docker
- Dokploy
- GitHub Actions
- VPS Ubuntu

---

# Deployment Architecture

Vendora is deployed using Dokploy on a VPS.

## Deployment Rules

- Every service must use Docker
- Every service must have its own Dockerfile
- Use docker-compose for local development
- Environment variables must be externalized
- Secrets must NEVER be hardcoded
- Services must support restart policies
- Applications must be stateless

---

# Dokploy Deployment Structure

## Services

```text
frontend
backend
```

## External Services

```text
Neon PostgreSQL
```

---

# Deployment Requirements

## Frontend

- Build using standalone output
- Use production mode
- Expose port 3000
- Environment variables injected by Dokploy

## Backend

- FastAPI served via uvicorn
- Expose port 8000
- Environment variables injected by Dokploy

---

# Environment Variables Rules

All secrets must come from Dokploy environment variables.

Example:

```env
DATABASE_URL=
JWT_SECRET=
NEXT_PUBLIC_API_URL=
```

Rules:

- NEVER hardcode secrets
- NEVER commit .env files
- ALWAYS validate env variables at startup

---

# Repository Structure

## Frontend

```text
frontend/
├── src/
│   ├── app/
│   ├── features/
│   ├── shared/
│   ├── core/
│   └── styles/
```

## Backend

```text
backend/
├── app/
│   ├── api/
│   ├── domain/
│   ├── repositories/
│   ├── services/
│   ├── models/
│   ├── schemas/
│   ├── infrastructure/
│   └── core/
```

---

# Architecture Rules

## Frontend Architecture

Frontend uses:

- Feature-based architecture
- Domain separation
- Shared component system
- SOLID principles

### Rules

- Do NOT place business logic in components
- Components must stay presentation-focused
- API calls belong inside services
- Shared logic belongs inside hooks
- State management must be isolated
- Avoid prop drilling

### Preferred Patterns

GOOD:

```ts
ProductCard.tsx
useProduct.ts
product.service.ts
```

BAD:

```ts
ProductCard.tsx
// fetch()
 // business logic
 // state mutation
```

---

## Backend Architecture

Backend follows Clean Architecture.

### Layer Responsibilities

| Layer | Responsibility |
|---|---|
| api | HTTP layer |
| services | business logic |
| repositories | database access |
| domain | business entities |
| schemas | validation |
| infrastructure | external services |

---

# SOLID Principles

All generated code must follow SOLID.

## S — Single Responsibility

Each module/class/component should have one responsibility.

## O — Open Closed

Prefer extension over modification.

## L — Liskov Substitution

Interfaces must be safely replaceable.

## I — Interface Segregation

Avoid large interfaces.

## D — Dependency Inversion

Depend on abstractions.

Example:

```python
class ProductRepositoryInterface:
    pass
```

NOT:

```python
class ProductService:
    def __init__(self, postgres):
        self.postgres = postgres
```

---

# Authentication Rules

Vendora uses JWT Authentication.

## Requirements

- Use JWT access token
- Use refresh token rotation
- Store refresh token securely
- Use HTTP-only cookies when possible
- Use RBAC authorization
- Validate token on protected routes

## Frontend

- Authentication state should be centralized
- Avoid duplicated auth logic
- Protect routes using middleware
- Use secure token storage

## Backend

- Validate JWT on every protected request
- Use middleware/dependencies for auth validation
- Never trust frontend authorization
- Use token expiration

---

# Neon Database Rules

Vendora uses Neon PostgreSQL.

## Requirements

- Use connection pooling
- Use migrations for all schema changes
- Never modify production schema manually
- Optimize indexes
- Use transactional operations for critical flows

## Best Practices

- Prefer UUIDs
- Use soft delete where necessary
- Avoid N+1 queries
- Use repository abstraction

---

# Docker Rules

## Requirements

- Multi-stage Docker builds preferred
- Images should stay lightweight
- Use .dockerignore
- Containers must be production-ready
- Avoid running containers as root

## Frontend Docker

- Use standalone Next.js output
- Use node:lts-alpine when possible

## Backend Docker

- Use slim Python images
- Install only production dependencies

---

# Frontend Standards

## Rules

- Use strict TypeScript
- No `any`
- Use server components where possible
- Minimize client components
- Use typed API responses
- Use reusable UI primitives

---

# Backend Standards

## Rules

- Use async APIs when possible
- Validate all input
- Never expose internal errors
- Use repository pattern
- Keep services stateless
- Avoid fat controllers

---

# API Standards

## REST Conventions

Use:

```text
/api/v1/products
/api/v1/transactions
```

## Response Format

```json
{
  "success": true,
  "data": {},
  "message": "Success"
}
```

---

# Security Rules

Agents must:

- Hash passwords securely
- Validate permissions
- Sanitize inputs
- Avoid SQL injection
- Never hardcode secrets
- Use environment variables
- Use secure cookies
- Rotate secrets when compromised

---

# Testing Rules

## Frontend

Required:
- unit tests

Preferred:
- component tests
- e2e tests

## Backend

Required:
- service tests

Preferred:
- integration tests

---

# Performance Rules

- Avoid unnecessary renders
- Use pagination
- Optimize database queries
- Use caching carefully
- Prevent N+1 queries

---

# Git Rules

## Branch Naming

```text
feature/
fix/
refactor/
hotfix/
```

## Commit Convention

```text
feat:
fix:
docs:
refactor:
test:
chore:
```

---

# Agent Behavior Rules

## Agents MUST

- preserve architecture boundaries
- write typed code
- create maintainable code
- reuse existing abstractions
- prefer composition
- add validation
- keep functions small

## Agents MUST NOT

- bypass repositories
- place SQL in controllers
- mix UI and business logic
- introduce circular dependencies
- duplicate logic
- create giant files

---

# Code Generation Preferences

## Prefer

- reusable abstractions
- small modules
- composition
- dependency injection
- pure functions

## Avoid

- massive utility files
- god objects
- tightly coupled modules
- hidden side effects

---

# Definition of Done

A task is complete when:

- feature works
- tests pass
- lint passes
- types pass
- documentation updated
- architecture respected
- Docker build passes
- Dokploy deployment works

---

# Long-Term Vision

Vendora should remain:

- scalable
- modular
- maintainable
- AI-agent friendly
- microservice-ready
- easy for new developers to onboard
