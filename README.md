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

### Ejecutar Tests

```bash
cd backend
pip install -r requirements.txt pytest pytest-asyncio aiosqlite httpx
pytest -v
```

### Estructura del Proyecto

```
sophie/
├── backend/          # FastAPI + SQLAlchemy + Alembic
│   ├── app/
│   │   ├── api/          # Endpoints REST
│   │   ├── core/         # Config, DB, seguridad
│   │   ├── infrastructure/models/  # 26 tablas ERD
│   │   └── schemas/      # Pydantic models
│   ├── tests/            # Suite de pruebas pytest
│   └── Dockerfile
├── frontend/         # Vue.js 3 + TypeScript + Tailwind CSS
│   ├── src/
│   │   ├── components/   # SidebarNav, TopBar, UI primitives
│   │   ├── layouts/      # MainLayout
│   │   ├── pages/        # Dashboard, Login, CRM, Ventas, etc.
│   │   ├── router/       # Vue Router (rutas protegidas)
│   │   ├── stores/       # Pinia stores (auth, clientes, tickets)
│   │   └── services/     # API client (Axios + interceptores)
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

---

## ✅ Estado del Proyecto

### Módulos Completados

| Módulo | Backend | Frontend | Tests |
|---|---|---|---|
| **Autenticación** (JWT + MFA/TOTP) | ✅ | ✅ | ✅ |
| **CRM — Clientes** (B2B/B2C, timeline) | ✅ | ✅ | ✅ |
| **Ventas & Cotizaciones** (facturación, stock) | ✅ | ✅ parcial | — |
| **Taller de Reparaciones** (tickets, repuestos, fotos) | ✅ | ✅ | — |
| **Soporte IT** (tickets, SLA, incidencias) | ✅ | ✅ | — |
| **Inventario** (productos, series, stock) | ✅ | ✅ | — |
| **Compras & Proveedores** (órdenes de compra, recepción) | ✅ | ✅ parcial | — |
| **Proyectos & Asesoría** (proyectos, tareas, tiempo) | ✅ | ✅ | ✅ |
| **Bóveda de Credenciales** (AES-256-GCM + MFA) | ✅ | ✅ | — |
| **Usuarios & Roles** (RBAC, admin) | ✅ | — | ✅ |
| **Dashboard** (estadísticas en tiempo real) | ✅ | ✅ | ✅ |
| **Auditoría** (log inmutable, acceso bóveda) | ✅ | — | — |

### Pendiente / Mejoras Futuras

- [ ] Formulario de creación de cotizaciones en el frontend (VentasPage)
- [ ] Vista de órdenes de compra en frontend (ComprasPage)
- [ ] Guardar cambios en el taller realmente llama a la API (TallerPage)
- [ ] Migraciones Alembic completas para producción
- [ ] Cobertura de tests para todos los módulos
- [ ] Notificaciones / alertas por email (Celery + SMTP)
- [ ] Reportes y exportación PDF/Excel
- [ ] Modo oscuro en el frontend

### Cómo Validar el Sistema

```bash
# 1. Backend: Ejecutar la suite de tests (23 tests, ~2s)
cd backend && pytest -v

# 2. Swagger UI interactiva (con Docker levantado)
open http://localhost:8000/docs

# 3. Flujo básico de validación manual:
#    a. Registrar admin: POST /api/v1/auth/register
#    b. Login:           POST /api/v1/auth/login
#    c. Dashboard:       GET  /api/v1/dashboard/stats
#    d. Crear cliente:   POST /api/v1/clientes/
#    e. Crear ticket:    POST /api/v1/tickets/
#    f. Crear proyecto:  POST /api/v1/proyectos/
```

