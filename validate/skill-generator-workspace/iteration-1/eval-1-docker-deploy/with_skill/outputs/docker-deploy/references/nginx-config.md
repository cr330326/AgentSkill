# Nginx Configuration Templates

Reference configurations for common reverse-proxy scenarios with Docker.

## Table of Contents

1. [Basic reverse proxy](#basic-reverse-proxy)
2. [With SSL termination](#with-ssl-termination)
3. [With rate limiting](#with-rate-limiting)
4. [Static files + API proxy](#static-files--api-proxy)
5. [WebSocket support](#websocket-support)
6. [Multiple upstream services](#multiple-upstream-services)

## Basic reverse proxy

Minimal config that forwards traffic to an upstream app service:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream app {
        server app:3000;
    }

    server {
        listen 80;
        server_name _;

        location / {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

## With SSL termination

Terminate SSL at Nginx and forward plain HTTP to the app:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream app {
        server app:3000;
    }

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name example.com;
        return 301 https://$host$request_uri;
    }

    server {
        listen 443 ssl;
        server_name example.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # HSTS
        add_header Strict-Transport-Security "max-age=63072000" always;

        location / {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

## With rate limiting

Protect against abuse with connection and request rate limits:

```nginx
http {
    # Define rate limit zones
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_conn_zone $binary_remote_addr zone=conn:10m;

    upstream app {
        server app:3000;
    }

    server {
        listen 80;

        location /api/ {
            limit_req zone=api burst=20 nodelay;
            limit_conn conn 10;

            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        location / {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

## Static files + API proxy

Serve static files directly from Nginx, proxy API requests to the app:

```nginx
http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    sendfile on;
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;

    upstream api {
        server app:3000;
    }

    server {
        listen 80;

        # Static files (built frontend)
        location / {
            root /usr/share/nginx/html;
            index index.html;
            try_files $uri $uri/ /index.html;  # SPA fallback
        }

        # API proxy
        location /api/ {
            proxy_pass http://api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
    }
}
```

## WebSocket support

Enable WebSocket connections through Nginx:

```nginx
http {
    map $http_upgrade $connection_upgrade {
        default upgrade;
        '' close;
    }

    upstream app {
        server app:3000;
    }

    server {
        listen 80;

        location / {
            proxy_pass http://app;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $connection_upgrade;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_read_timeout 86400;  # Keep WebSocket alive
        }
    }
}
```

## Multiple upstream services

Route traffic to different backends based on path:

```nginx
http {
    upstream frontend {
        server frontend:3000;
    }

    upstream api {
        server api:8080;
    }

    upstream admin {
        server admin:4000;
    }

    server {
        listen 80;

        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
        }

        location /api/ {
            proxy_pass http://api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        location /admin/ {
            proxy_pass http://admin;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```
