# BrandMind customer portal and support dashboard

BrandMind builds two independent frontends from the same React/Vite source tree and connects both to the existing FastAPI service and shared conversation database:

- **Customer portal:** a public, lightweight support chat. It uses a guest session cookie and shows only conversations owned by that browser session. Customers can start a new chat, return to their history, send messages and attachments, and receive AI or agent replies.
- **Support Team Dashboard:** an internal inbox for support employees. Staff sign in with the shared email/password configured on the API; the API returns a bearer token for protected dashboard requests. The dashboard provides conversation monitoring, takeovers/replies, customer and order details, analytics, and Technical Inspector traces. It does not offer a customer preview mode.

There is no customer selector, customer preview route, or admin UI in the public customer build. The frontend build separation is not the authorization boundary: FastAPI continues to enforce guest ownership and admin authentication independently. Both frontends share the same backend and records.

The API stores conversations in `results/conversations.sqlite3`. The existing `AgentOrchestrator` remains responsible for AI replies and execution traces. Inbox refresh uses polling (about 1.8 seconds for inbox rows and 1 second for the active thread).

## Run locally

Start FastAPI from the repository root:

```powershell
py -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --reload
```

Start the support dashboard:

```powershell
cd web
npm install
npm run dev
```

Open `http://127.0.0.1:5173/` for the Support Team Dashboard. The customer portal runs independently at `http://127.0.0.1:5174/`:

```powershell
npm run dev:customer
```

The local `.env` is configured with the requested shared support account. The API checks `BRANDMIND_ADMIN_EMAIL` and `BRANDMIND_ADMIN_PASSWORD` and rate limits failed sign-in attempts. In development, if `BRANDMIND_ADMIN_TOKEN` is unset, the API creates a random admin bearer token in memory after successful email/password authentication; it is not a predictable default token. For production, set `ENVIRONMENT=production`, a private `BRANDMIND_ADMIN_TOKEN`, and a strong password of at least 12 characters. Weak passwords are rejected in production. All support employees currently share this one account; individual staff accounts, roles, and per-agent audit identity are not implemented. Keep the `.env` file private and do not copy credentials into the customer frontend.

Set `VITE_API_URL` before building/starting either frontend if FastAPI uses a different origin; the default is `http://127.0.0.1:8000/api/v1`. This value is compiled into the frontend bundle and must not contain secrets.

## Separate frontend builds and deployment

Build both frontends with `npm run build`. The output directories are:

- `web/dist/customer/` — publish on the public customer support domain.
- `web/dist/support/` — publish on the private/internal support domain, protected by your identity-aware proxy/VPN or equivalent network access control in addition to the dashboard's API token.

Each output has its own `index.html` and assets and may be deployed as a separate static site. Both sites must point `VITE_API_URL` at the same FastAPI API. Hosting must return that site's `index.html` for its frontend routes and static assets; forward `/api/v1/*` to FastAPI and do not rewrite API errors to an HTML page. The support login page is not a substitute for network access controls or individual employee authentication. Since staff share a token, use a secret manager and rotate it if exposed.

## Customer session and conversation security

The browser creates or resumes a customer guest session with `POST /api/v1/customer/session`. FastAPI generates a 256-bit random secret, stores only its SHA-256 digest, and sets the secret in the host-only `brandmind_customer_session` cookie (`HttpOnly`, `Path=/api/v1`). The JSON response contains a CSRF token and expiry, but never the session secret. The React app keeps the CSRF token in component memory and sends it as `X-CSRF-Token` on customer conversation creation and message submission. Do not copy the session cookie into JavaScript storage or logs.

Customer sessions expire after 30 days by default. Configure `BRANDMIND_CUSTOMER_SESSION_TTL_DAYS` (1–365) to change that. `BRANDMIND_CUSTOMER_COOKIE_SAMESITE` defaults to `lax`. In development the cookie is not `Secure` so it works over local HTTP. `ENVIRONMENT=production` always enables `Secure`; production must use HTTPS. If the portal and API are cross-site, set SameSite to `none` (which also enables `Secure`) and deploy both over HTTPS. Prefer same-site origins with `lax`.

Set `BRANDMIND_CORS_ORIGINS` to the exact comma-separated frontend origins allowed to call the API with cookies. Local defaults include `http://127.0.0.1:5173`, `http://localhost:5173`, `http://127.0.0.1:5174`, and `http://localhost:5174`. In production, list the actual customer and support origins; this setting is required and must not use `*` with credentials. Cookie-authenticated writes require an allowed `Origin` and matching CSRF header.

New conversations link to the guest session digest. `GET /api/v1/customer/conversations` returns only rows owned by the current session. Existing conversations remain unowned and are not exposed to guest sessions; authenticated admin endpoints retain access to historical records. Customer reads, message writes, and attachment downloads return the same 404 for missing, legacy, or differently owned conversations.

The two Vite origins are both same-site during local development (`127.0.0.1` on ports 5173 and 5174), so the default `SameSite=Lax` cookie works. For production, configure the cookie and CORS origins to match the chosen portal/API domain layout, and verify cookies are sent with credentials.

## Data retention and deployment boundaries

When a customer starts a new chat, the previous chat is marked **Ignored by customer**, removed from that customer's history immediately, and kept in the support dashboard's ignored view for 48 hours. The API background cleanup checks every five minutes and purges expired customer-ignored conversations, their messages, and attachment files. Audit logs are retained. Set `BRANDMIND_CUSTOMER_IGNORED_TTL_HOURS` to change this window. Other resolved/ignored conversations are retained; this cleanup only applies to customer-initiated ignores.

- The store and takeover lock are local SQLite and in-process. Run one API worker. Horizontal deployment requires a shared database and distributed coordination.
- Customer access is tied to a browser guest session, not a verified identity. Clearing cookies loses access to that session's conversations.
- Order records remain synthetic CSV data.
- Inbox refresh uses polling; no WebSocket is introduced here.
