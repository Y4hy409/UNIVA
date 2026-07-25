# ADR-010: Hierarchical Settings Architecture

## Status

**Accepted** — 2026-07-19

## Context

CLARIUS configuration spans application runtime, organization profile, licensing, integrations, AI parameters, user preferences, and themes. A single monolithic `settings.enc` file becomes unmaintainable, hard to migrate, and risky to partially update (one bad write corrupts everything).

---

## Decision

Implement **hierarchical, namespaced settings** stored as separate encrypted files under `{CLARIUS_DATA_ROOT}/settings/`, managed by `infrastructure/settings/`.

### Settings Hierarchy

```
Settings
├── application/          # Runtime, ports, CORS, logging, data root
├── organization/         # Company name, GSTIN, branches, fiscal year
├── license/              # Cached license metadata (not the license file itself)
├── integrations/         # ERP connections, API endpoints (secrets → vault)
├── ai/                   # Ollama model, temperature, agent config
├── users/                # Default roles, session TTL, lockout policy
└── themes/               # UI theme, density, locale, date format
```

### Storage Layout

```
{CLARIUS_DATA_ROOT}/settings/
├── _version.json                    # Settings schema version (for migrations)
├── application.enc
├── organization.enc
├── integrations.enc
├── ai.enc
├── users.enc
├── themes.enc
└── rbac.yaml                          # RBAC matrix (plaintext, non-secret)
```

Each `.enc` file: AES-256-GCM encrypted JSON blob. Encryption key derived from machine-specific seed + master key in vault.

### Settings Schema Examples

**application.enc (decrypted):**

```json
{
  "api_port": 8741,
  "api_bind": "0.0.0.0",
  "deployment_mode": "office_lan",
  "cors_origins": ["http://192.168.1.0/24"],
  "log_level": "INFO",
  "data_root": null,
  "language": "en",
  "timezone": "Asia/Kolkata"
}
```

**organization.enc:**

```json
{
  "name": "ACME Traders Pvt Ltd",
  "gstin": "27AABCU9603R1ZM",
  "fiscal_year_start_month": 4,
  "currency": "INR",
  "currency_symbol": "₹",
  "branches": [
    { "id": "main", "name": "Head Office", "is_default": true }
  ]
}
```

**ai.enc:**

```json
{
  "ollama_base_url": "http://localhost:11434",
  "default_model": "qwen3:4b-instruct",
  "sql_temperature": 0.1,
  "analysis_temperature": 0.3,
  "max_query_rows": 1000,
  "max_concurrent_llm_calls": 1,
  "embedding_model": "all-MiniLM-L6-v2"
}
```

**themes.enc:**

```json
{
  "mode": "system",
  "density": "comfortable",
  "date_format": "DD/MM/YYYY",
  "number_format": "en-IN",
  "primary_color": null
}
```

### SettingsService Interface

```python
class ISettingsService(Protocol):
    async def get(self, namespace: str, key: str, default: Any = None) -> Any: ...
    async def get_namespace(self, namespace: str) -> dict: ...
    async def set(self, namespace: str, key: str, value: Any) -> None: ...
    async def update_namespace(self, namespace: str, values: dict) -> None: ...
```

### Access Control

| Namespace | Read | Write |
|-----------|------|-------|
| application | All authenticated | Admin |
| organization | All authenticated | Admin |
| integrations | Admin, Manager | Admin |
| ai | Admin, Analyst | Admin |
| users | Admin | Admin |
| themes | All authenticated | User (own theme) / Admin (defaults) |
| license | All authenticated | Owner only (via license import flow) |

### API Endpoints

```
GET    /settings/{namespace}              # Get namespace (filtered by role)
PATCH  /settings/{namespace}              # Partial update
GET    /settings/application/public         # Unauthenticated startup config (port, mode)
```

**Rule:** Secrets in integrations (API keys, passwords) stored in `secrets/vault.enc`. Settings store **references** only:

```json
{
  "erpnext": {
    "enabled": true,
    "base_url": "http://192.168.1.50:8000",
    "api_key_ref": "vault:integrations.erpnext.api_key"
  }
}
```

### Frontend Settings UI

`apps/desktop/src/features/settings/` organized by namespace tabs:

```
Settings
├── General (application + organization)
├── Integrations
├── AI Configuration
├── Users & Roles
├── Appearance (themes)
└── License
```

Each tab maps 1:1 to a settings namespace.

### Caching

- In-memory cache per namespace with TTL (60s)
- Invalidated on PATCH
- Event bus publishes `SettingsChanged` for subscribers (e.g., AI client reconnect)

### Default Initialization

First-run setup wizard writes:
1. `organization` — company name from wizard
2. `users` — session defaults
3. `application` — deployment mode selection
4. `ai` — defaults (Ollama localhost)
5. `themes` — system defaults

---

## Consequences

### Positive

- Partial updates without corrupting entire config
- Namespace-level migrations (ADR-009)
- Clear RBAC per settings area
- Frontend settings UI maps cleanly to backend

### Negative

- Multiple encrypted files to manage
- Cross-namespace validation needed (e.g., branch in organization vs data source branch)

---

## Alternatives Considered

| Alternative | Disadvantage |
|-------------|--------------|
| Single settings.enc | Migration pain; corruption risk |
| DuckDB settings table | Mixes config with business data |
| Plaintext JSON files | Secrets exposure risk |

---

## References

- ADR-001: Settings directory layout
- ADR-003: RBAC for settings access
- ADR-009: Settings schema migrations
