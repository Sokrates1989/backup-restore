# 🔐 Security & Authentication Options (Backup-Restore)

This document compares authentication approaches for the Backup-Restore tool and explains what it *does and does not* mean to host the Admin UI separately from the API.

## Context

- **What this app is**
  - A privileged *admin tool* that can trigger backups/restores (high impact).
  - A static Admin UI (SPA) and an API.

- **What you have today**
  - API endpoints guarded by shared secrets (e.g. `X-Admin-Key`, `X-Delete-Key`, `X-Restore-Key`).
  - CSP/security headers are enabled and the UI avoids inline scripts/handlers.

## Threat model (what you should defend against)

- **Stolen admin secret/JWT**
  - Gives an attacker the ability to exfiltrate backups or destroy/overwrite databases.
- **Accidental exposure of the UI/API to the public internet**
  - Common via port-forwarding, cloud security group mistakes, misconfigured reverse proxies.
- **XSS in the Admin UI**
  - If tokens are stored in `localStorage`, XSS becomes “token theft”.
- **Brute force / credential stuffing** (if you add password login)
- **CSRF** (if you switch to cookie-based auth)

## Hosting the Admin UI separately: what changes (and what doesn’t)

### ✅ What hosting separately can improve

- **Edge protections**
  - You can put the UI behind a CDN/WAF, HTTP auth, IP allowlisting, mTLS, etc.
- **Simpler static hosting**
  - UI can live on a static host (S3/CloudFront, Netlify, nginx-only, etc.) with fast caching.

### ❌ What hosting separately does *not* automatically improve

- **Auth boundary**
  - The *real* boundary is the API. If the API is still reachable with a shared secret, the UI location doesn’t matter much.
- **Secret exposure risk**
  - If the UI still asks for a long-lived admin secret and stores it in browser storage, hosting separately doesn’t reduce the blast radius.

### Key decision: “Browser calls API directly” vs “Proxy calls API”

1) **Browser calls API directly** (SPA → API)
   - Needs CORS if origins differ.
   - You should use **OIDC/JWT** (preferred) or short-lived tokens.
   - Avoid long-lived secrets in the browser.

2) **Reverse proxy calls API** (User → Proxy → API)
   - The proxy enforces auth (Basic Auth, OAuth2 forward auth, IP allowlist).
   - The browser can remain “dumb”, and the API is reachable only behind the proxy.
   - This is often the easiest “secure enough” approach for admin tools.

## Options overview (recommended paths)

### Option A: Keep API keys (current) + put everything behind a private network

- **Use when**
  - This is a personal/internal tool.
  - You can rely on VPN / private network / IP allowlists.

- **Hardening checklist**
  - Keep API ports private (VPN, tailscale, security group allowlist).
  - Rotate keys regularly.
  - Prefer separate keys for read/backup/restore/delete (already supported).
  - Add rate limiting at the reverse proxy.

### Option B: Reverse-proxy authentication (no app-level auth)

- **Use when**
  - You want SSO/login *without changing the app much*.

- **Common patterns**
  - nginx/Traefik Basic Auth + IP allowlist.
  - `oauth2-proxy` (OIDC) in front of the UI/API.
  - Traefik “forwardAuth” middleware.

- **Notes**
  - The API should ideally not be directly reachable from the internet, only via the proxy.

### Option C: Full OIDC in the app (JWT verification in API)

- **Use when**
  - You want proper user identities, roles, auditability, revocation, MFA.

- **Implementation shape**
  - UI uses OAuth2 Authorization Code + PKCE.
  - API validates JWT (issuer, audience, exp) via JWKS.
  - Use roles/claims for authorization (admin, restore, delete).

## Provider comparison

### Summary table

| Provider | Hosted? | Best for | Pros | Cons |
|---|---:|---|---|---|
| **Keycloak** | Self-host | Full-featured IAM, SSO | Very powerful, mature, roles/groups, OIDC/SAML, MFA, good admin UI | You operate it (updates, DB), can be heavy for small installs |
| **AWS Cognito** | Managed | AWS-centric setups | Low ops, integrates with AWS, OIDC/JWT | UX/admin can be awkward, customization friction, AWS lock-in |
| **Auth0** | Managed | Fast rollout SaaS | Great DX, rules/actions, docs | Cost can grow quickly, external dependency |
| **Azure AD / Entra ID** | Managed | Microsoft orgs | Enterprise SSO, conditional access | Not ideal for hobby/self-host unless you’re already in Microsoft ecosystem |
| **Supabase Auth** | Hosted/self-host | Small/medium apps | Simple, Postgres ecosystem | Not as enterprise-rich as Keycloak; self-host still ops |
| **Ory (Kratos/Hydra)** | Self-host | Composable auth | Very flexible, modern | More engineering/assembly required than Keycloak |

### Keycloak (details)

- ✅ **Strengths**
  - Best self-hosted “all-in-one” identity provider.
  - Good for role-based access (`admin`, `restore`, `delete`).
  - Supports MFA and many federation options.

- ⚠️ **Operational considerations**
  - You run Keycloak + its database (usually Postgres).
  - Needs patching and config backups.

### AWS Cognito (details)

- ✅ **Strengths**
  - Managed service (minimal ops).
  - JWT verification is standard OIDC (issuer/audience/JWKS).

- ⚠️ **Considerations**
  - Custom flows and UI are often the “hard part”.
  - Costs are usually fine for small user counts, but track MAUs.

## Recommendation for this project

If this stays an **admin-only tool**:

1) Put UI+API behind a reverse proxy with **IP allowlisting + Basic Auth** or **OIDC forward-auth**.
2) Keep the existing API keys as an additional “second factor” for the most dangerous operations (`restore`, `delete`).

If this becomes **multi-user / production**:

1) Implement full OIDC in the API (JWT verification).
2) Use Keycloak (self-host) or Cognito (managed) depending on whether you want **ops control** vs **managed convenience**.

## Notes on token storage (Admin UI)

- Prefer **in-memory** storage for access tokens.
- Avoid long-lived secrets in `localStorage`.
- If you need persistence, prefer short-lived access token + refresh token with careful handling.

## Deployment patterns (quick guide)

- **Best “simple + secure”**
  - UI+API on private network + reverse proxy auth.

- **Best “internet-facing”**
  - Reverse proxy with OIDC auth in front of UI/API **and** API does JWT verification.
  - Add rate limiting + WAF rules.