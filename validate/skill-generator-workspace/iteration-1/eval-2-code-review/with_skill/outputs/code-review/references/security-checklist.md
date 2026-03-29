# Security Review Checklist

Derived from OWASP Top 10 and common vulnerability patterns. Use during Step 3 (Security Review)
of the code review workflow.

## Table of Contents

1. [Injection](#injection)
2. [Broken Authentication](#broken-authentication)
3. [Sensitive Data Exposure](#sensitive-data-exposure)
4. [Broken Access Control](#broken-access-control)
5. [Security Misconfiguration](#security-misconfiguration)
6. [Cross-Site Scripting (XSS)](#cross-site-scripting-xss)
7. [Insecure Deserialization](#insecure-deserialization)
8. [Dependency Vulnerabilities](#dependency-vulnerabilities)
9. [Logging and Monitoring](#logging-and-monitoring)
10. [API Security](#api-security)

---

## Injection

- [ ] SQL queries use parameterized statements or an ORM -- never string concatenation
- [ ] NoSQL queries sanitize user input (especially MongoDB `$where`, `$gt`, etc.)
- [ ] Shell commands never include unsanitized user input; use exec arrays instead of shell strings
- [ ] LDAP queries escape special characters in user-supplied values
- [ ] Template engines auto-escape by default; manual `| safe` or `{!! !!}` usage is justified
- [ ] Regular expressions from user input are sanitized to prevent ReDoS

## Broken Authentication

- [ ] Passwords are hashed with bcrypt, scrypt, or argon2 -- never MD5, SHA1, or SHA256 alone
- [ ] Login endpoints have rate limiting or account lockout
- [ ] Session tokens are generated with cryptographically secure randomness
- [ ] JWTs validate signature, issuer, audience, and expiration
- [ ] JWT secret keys are sufficiently strong (256+ bits for HMAC, RSA 2048+ for asymmetric)
- [ ] Refresh token rotation is implemented; old refresh tokens are invalidated
- [ ] Password reset tokens expire quickly (< 1 hour) and are single-use
- [ ] Multi-factor authentication is available for sensitive operations

## Sensitive Data Exposure

- [ ] Passwords, tokens, and API keys are never logged
- [ ] Error messages don't reveal stack traces, database schemas, or internal paths to end users
- [ ] API responses exclude sensitive fields (password hashes, SSNs, internal IDs)
- [ ] PII is encrypted at rest in the database
- [ ] TLS is enforced for all external communication
- [ ] Secrets are loaded from environment variables or a secret manager -- never hardcoded
- [ ] `.env` files and credential files are in `.gitignore`

## Broken Access Control

- [ ] Every API endpoint checks authentication
- [ ] Authorization checks verify the requesting user has access to the specific resource (not just role)
- [ ] IDOR (Insecure Direct Object Reference) is prevented -- users can't access other users' data by changing an ID
- [ ] Admin endpoints are protected by role checks, not just hidden URLs
- [ ] File upload paths are sanitized to prevent directory traversal
- [ ] CORS configuration is restrictive -- not `Access-Control-Allow-Origin: *` for authenticated endpoints

## Security Misconfiguration

- [ ] Debug mode is disabled in production configurations
- [ ] Default credentials are changed or removed
- [ ] Security headers are set: `Content-Security-Policy`, `X-Content-Type-Options`, `Strict-Transport-Security`
- [ ] Directory listing is disabled on web servers
- [ ] Error handling doesn't reveal implementation details
- [ ] Unnecessary HTTP methods (TRACE, OPTIONS) are disabled

## Cross-Site Scripting (XSS)

- [ ] User input rendered in HTML is escaped by the template engine
- [ ] `dangerouslySetInnerHTML` (React) or `v-html` (Vue) usage is justified and input is sanitized
- [ ] URLs from user input are validated against an allowlist of schemes (`http:`, `https:`)
- [ ] Content-Security-Policy header restricts inline scripts and eval
- [ ] SVG uploads are sanitized (SVGs can contain JavaScript)

## Insecure Deserialization

- [ ] Deserialization of untrusted data uses safe parsers (JSON.parse, not eval)
- [ ] Object deserialization libraries have type restrictions (no arbitrary class instantiation)
- [ ] Protobuf/MessagePack/YAML parsers are configured to reject unknown types
- [ ] YAML loading uses safe mode (no `!!python/object` or equivalent)

## Dependency Vulnerabilities

- [ ] New dependencies are checked for known CVEs (`npm audit`, `pip audit`, `cargo audit`)
- [ ] Dependencies are pinned to specific versions (lock files committed)
- [ ] New dependencies are from reputable sources (check download counts, maintenance status)
- [ ] Package names are verified (typosquatting check)
- [ ] Dependency scope is appropriate (dev-only deps aren't in production)

## Logging and Monitoring

- [ ] Authentication events (login, logout, failure) are logged
- [ ] Authorization failures are logged with context
- [ ] Logs don't contain sensitive data (passwords, tokens, PII)
- [ ] Log injection is prevented (user input in log messages is sanitized)
- [ ] Rate limiting is in place for public-facing endpoints

## API Security

- [ ] Input validation is applied at the API boundary (type, length, format, range)
- [ ] Response pagination is enforced with maximum page sizes
- [ ] File uploads are restricted by type, size, and scanned for malware
- [ ] GraphQL queries have depth and complexity limits
- [ ] WebSocket connections are authenticated and authorized
- [ ] API versioning strategy handles deprecated endpoints gracefully
