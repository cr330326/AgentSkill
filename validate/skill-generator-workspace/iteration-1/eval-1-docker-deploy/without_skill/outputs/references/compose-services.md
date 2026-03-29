# Compose Service Blocks

Pre-built service definitions for common infrastructure components. Copy and adapt as needed.

## Reverse Proxies

### Nginx (as reverse proxy)

```yaml
  nginx:
    image: nginx:1.25-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./nginx/certs:/etc/nginx/certs:ro
      - nginx-logs:/var/log/nginx
    depends_on:
      app:
        condition: service_healthy
    networks:
      - app-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 5s
      retries: 3
```

**Sample `nginx/conf.d/default.conf`:**
```nginx
upstream app_backend {
    server app:3000;
}

server {
    listen 80;
    server_name example.com;

    location / {
        proxy_pass http://app_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Traefik (with automatic SSL)

```yaml
  traefik:
    image: traefik:v3.0
    command:
      - "--api.dashboard=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
      - "--certificatesresolvers.letsencrypt.acme.email=${ACME_EMAIL}"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
      - "--entrypoints.web.http.redirections.entrypoint.to=websecure"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - traefik-certs:/letsencrypt
    networks:
      - app-network
    restart: unless-stopped

  # Then add labels to your app service:
  # labels:
  #   - "traefik.enable=true"
  #   - "traefik.http.routers.app.rule=Host(`example.com`)"
  #   - "traefik.http.routers.app.entrypoints=websecure"
  #   - "traefik.http.routers.app.tls.certresolver=letsencrypt"
  #   - "traefik.http.services.app.loadbalancer.server.port=3000"
```

### Caddy (with automatic SSL)

```yaml
  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy-data:/data
      - caddy-config:/config
    depends_on:
      app:
        condition: service_healthy
    networks:
      - app-network
    restart: unless-stopped
```

**Sample `Caddyfile`:**
```
example.com {
    reverse_proxy app:3000
}
```

## Databases

### PostgreSQL

```yaml
  postgres:
    image: postgres:16-alpine
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./initdb:/docker-entrypoint-initdb.d:ro  # Optional: init scripts
    environment:
      POSTGRES_DB: ${DB_NAME:-app}
      POSTGRES_USER: ${DB_USER:-app}
      POSTGRES_PASSWORD: ${DB_PASSWORD:?DB_PASSWORD is required}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-app} -d ${DB_NAME:-app}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    networks:
      - app-network
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M
```

### MySQL

```yaml
  mysql:
    image: mysql:8.0
    volumes:
      - mysql-data:/var/lib/mysql
    environment:
      MYSQL_DATABASE: ${DB_NAME:-app}
      MYSQL_USER: ${DB_USER:-app}
      MYSQL_PASSWORD: ${DB_PASSWORD:?DB_PASSWORD is required}
      MYSQL_ROOT_PASSWORD: ${DB_ROOT_PASSWORD:?DB_ROOT_PASSWORD is required}
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p${DB_ROOT_PASSWORD}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    networks:
      - app-network
    restart: unless-stopped
```

### MongoDB

```yaml
  mongo:
    image: mongo:7
    volumes:
      - mongo-data:/data/db
    environment:
      MONGO_INITDB_ROOT_USERNAME: ${MONGO_USER:-admin}
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD:?MONGO_PASSWORD is required}
      MONGO_INITDB_DATABASE: ${MONGO_DB:-app}
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - app-network
    restart: unless-stopped
```

## Caches

### Redis

```yaml
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD:-}
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - app-network
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 256M
```

### Memcached

```yaml
  memcached:
    image: memcached:1.6-alpine
    command: memcached -m 128
    healthcheck:
      test: ["CMD-SHELL", "echo stats | nc localhost 11211 | grep pid"]
      interval: 10s
      timeout: 5s
      retries: 3
    networks:
      - app-network
    restart: unless-stopped
```

## Message Queues

### RabbitMQ

```yaml
  rabbitmq:
    image: rabbitmq:3-management-alpine
    environment:
      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER:-guest}
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD:-guest}
    volumes:
      - rabbitmq-data:/var/lib/rabbitmq
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "-q", "ping"]
      interval: 15s
      timeout: 10s
      retries: 5
    networks:
      - app-network
    restart: unless-stopped
    # Management UI on port 15672 (don't expose in production)
    # ports:
    #   - "15672:15672"
```

### NATS

```yaml
  nats:
    image: nats:2-alpine
    command: "--jetstream --store_dir /data"
    volumes:
      - nats-data:/data
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:8222/healthz"]
      interval: 10s
      timeout: 5s
      retries: 3
    networks:
      - app-network
    restart: unless-stopped
```

## Monitoring

### Prometheus + Grafana

```yaml
  prometheus:
    image: prom/prometheus:v2.50.0
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.retention.time=15d"
    networks:
      - app-network
    restart: unless-stopped

  grafana:
    image: grafana/grafana:10.3.1
    volumes:
      - grafana-data:/var/lib/grafana
    environment:
      GF_SECURITY_ADMIN_USER: ${GRAFANA_USER:-admin}
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}
    depends_on:
      - prometheus
    networks:
      - app-network
    restart: unless-stopped
    # Access via reverse proxy in production, not direct port exposure
    # ports:
    #   - "3001:3000"
```

## Logging

### Loki + Promtail (with Grafana)

```yaml
  loki:
    image: grafana/loki:2.9.4
    command: "-config.file=/etc/loki/local-config.yaml"
    volumes:
      - loki-data:/loki
    networks:
      - app-network
    restart: unless-stopped

  promtail:
    image: grafana/promtail:2.9.4
    volumes:
      - /var/log:/var/log:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./promtail/config.yml:/etc/promtail/config.yml:ro
    networks:
      - app-network
    restart: unless-stopped
```

## S3-Compatible Object Storage

### MinIO

```yaml
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_USER:-minio}
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD:?MINIO_PASSWORD is required}
    volumes:
      - minio-data:/data
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - app-network
    restart: unless-stopped
```

## Full Volume and Network Declarations

Remember to declare all named volumes and networks at the bottom of your compose file:

```yaml
volumes:
  postgres-data:
  redis-data:
  mongo-data:
  mysql-data:
  rabbitmq-data:
  nats-data:
  minio-data:
  prometheus-data:
  grafana-data:
  loki-data:
  nginx-logs:
  traefik-certs:
  caddy-data:
  caddy-config:

networks:
  app-network:
    driver: bridge
```
