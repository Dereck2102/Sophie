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
# Prometheus:   http://localhost:9090
# Loki API:     http://localhost:3100
# Elasticsearch:http://localhost:9200
# Kibana:       http://localhost:5601
```

### Observabilidad (Prometheus + Loki + ELK)

- `Prometheus` scrapea métricas HTTP del backend desde `GET /metrics`.
- `Loki` recibe logs de contenedores vía `Promtail`.
- `ELK` recibe logs de contenedores vía `Filebeat -> Logstash -> Elasticsearch`.

Rutas útiles:

- Métricas backend: `http://localhost:8000/metrics`
- Targets Prometheus: `http://localhost:9090/targets`
- Kibana (Discover): `http://localhost:5601`

Notas:

- En Kibana crea un Data View con patrón `sophie-logs-*`.
- Prometheus es para métricas/series temporales; la visualización de logs se hace en Loki o ELK.

### Bootstrap Inicial

- La base de datos puede iniciarse vacía; el primer registro en `POST /api/v1/auth/register` crea automáticamente la cuenta `superadmin`.
- Ese primer usuario queda con correo verificado y acceso total a configuración, auditoría y restauración.
- Las cuentas `superadmin` solo pueden ser gestionadas por otro `superadmin`.

### Ejecutar Tests

```bash
cd backend
pip install -r requirements.txt pytest pytest-asyncio aiosqlite httpx
pytest -v
```

```bash
cd frontend
npm install
npm run build
```

### Port Desktop y Móvil (Electron + Capacitor)

`Electron` está configurado para empaquetar versión de escritorio (Windows/macOS/Linux).
Para port móvil real (`Android`/`iOS`) se usa `Capacitor`.

```bash
cd frontend
npm install

# Desktop (desarrollo)
npm run electron:dev

# Desktop (paquete instalable)
npm run electron:build

# Inicializar plataformas móviles (una sola vez)
npm run mobile:add:android
npm run mobile:add:ios

# Sincronizar build web y abrir plataforma
npm run mobile:android
npm run mobile:ios
```

Notas:
- Para Android necesitas Android Studio + SDK configurado.
- Para iOS necesitas macOS + Xcode.
- En móvil se reutiliza el frontend Vue compilado (`frontend/dist`) vía Capacitor.

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
| **Usuarios & Roles** (RBAC, superadmin, permisos granulares) | ✅ | ✅ | ✅ |
| **Dashboard** (estadísticas en tiempo real) | ✅ | ✅ | ✅ |
| **Auditoría** (log global, vista superadmin) | ✅ | ✅ | — |
| **Configuración Global** (branding, seguridad, backup/restore) | ✅ | ✅ | — |

### Pendiente / Mejoras Futuras

- [ ] Formulario de creación de cotizaciones en el frontend (VentasPage)
- [ ] Vista de órdenes de compra en frontend (ComprasPage)
- [ ] Migraciones Alembic completas para producción
- [ ] Cobertura de tests para todos los módulos
- [ ] Notificaciones / alertas por email (Celery + SMTP)
- [ ] Reportes y exportación PDF/Excel
- [ ] Modo oscuro en el frontend

### Capacidades Administrativas Nuevas

- `superadmin`: acceso exclusivo a auditoría, configuración global y restauración.
- Configuración persistente del sistema: nombre de instancia, empresa, RUC, logo, colores, timeout de sesión, MFA global y políticas de acceso.
- Backup y restore de usuarios/configuración desde el frontend administrativo.
- Auditoría HTTP global con módulo, acción, usuario, IP, estado y duración.
- Permisos, vistas y herramientas granulares por usuario además del rol base.

### Credentials Iniciales

**Superadmin Root:**
- **Username:** `root`
- **Password:** `RootPass123!`
- **Role:** `superadmin`
- **MFA:** Deshabilitado
- **Status:** Completamente funcional

**Superadmin Damacoria:**
- **Username:** `damacoria`
- **Email:** `amacoriadereck@gmail.com`
- **Password:** `Docedos13`
- **Role:** `superadmin`
- **MFA:** Deshabilitado (puede habilitarse después del primer login)
- **Status:** Completamente funcional

### Cómo Validar el Sistema

```bash
# 1. Backend: Ejecutar la suite de tests
cd backend && pytest -v

# 2. Frontend: validar compilación
cd ../frontend && npm run build

# 3. Swagger UI interactiva (con Docker levantado)
open http://localhost:8000/docs

# 4. Flujo básico de validación manual:
#    a. Login como damacoria:        POST /api/v1/auth/login
#    b. Obtener perfil:             GET  /api/v1/usuarios/me
#    c. Dashboard:                  GET  /api/v1/dashboard/stats
#    d. Configuración pública:      GET  /api/v1/admin/settings/public
#    e. Auditoría:                  GET  /api/v1/admin/auditoria
#    f. Crear cliente:              POST /api/v1/clientes/
#    g. Crear ticket:               POST /api/v1/tickets/
#    h. Configuración privada:      GET  /api/v1/admin/settings/private (solo superadmin)
```

---

## 📋 Notas de Deployment

- **Ambiente de Desarrollo:** Las credenciales están registradas en el README. En producción, usar gestión segura de secretos (Vault, AWS Secrets Manager, etc.).
- **Base de Datos:** PostgreSQL 15 inicialmente sin credenciales persistentes. En producción, usar variables de entorno sensitivas.
- **JWT Secret:** `dev_secret_key_change_in_production` debe reemplazarse en `docker-compose.yml`.
- **CORS:** Actualmente permite `localhost:3000`, `localhost`, `localhost:5173`. Ajustar según dominio de producción.

