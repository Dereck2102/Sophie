# SOPHIE — Sistema de Gestión ERP/CRM

> **Big Solutions** — Departamento de TI  
> Líder Técnico: Ing. Dereck Amacoria  
> Versión: 1.0.0

## 🚀 Quick Start

### Requisitos
- Docker 24+
- Docker Compose

### Desarrollo

```bash
# Levantar todo el stack
docker-compose up --build

# Acceder a:
# Frontend:     http://localhost:5173
# Backend API:  http://localhost:8000
# Swagger Docs: http://localhost:8000/docs
# Nginx Proxy:  http://localhost
```

### Estructura del Proyecto

```
sophie/
├── backend/          # FastAPI + SQLAlchemy + Alembic
│   ├── app/
│   │   ├── api/          # Endpoints REST
│   │   ├── core/         # Config, DB, seguridad
│   │   ├── domain/       # Entidades, interfaces
│   │   ├── infrastructure/models/  # 26 tablas ERD
│   │   └── services/     # Lógica de negocio
│   ├── alembic/          # Migraciones
│   └── Dockerfile
├── frontend/         # Vue.js 3 + TypeScript + Tailwind CSS
│   ├── src/
│   │   ├── components/   # SidebarNav, TopBar
│   │   ├── layouts/      # MainLayout
│   │   ├── pages/        # Dashboard, Login, etc.
│   │   ├── router/       # Vue Router
│   │   └── services/     # API client (Axios)
│   └── Dockerfile
├── nginx/            # Proxy inverso
├── docker-compose.yml
└── README.md
```

## 📦 Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Frontend | Vue.js 3 + TypeScript + Vite |
| Estilos | Tailwind CSS v4 |
| Estado | Pinia |
| Backend | Python 3.11 + FastAPI |
| Base de Datos | PostgreSQL 15 |
| ORM | SQLAlchemy 2.0 (async) |
| Contenedores | Docker + Docker Compose |
| Proxy | Nginx |
