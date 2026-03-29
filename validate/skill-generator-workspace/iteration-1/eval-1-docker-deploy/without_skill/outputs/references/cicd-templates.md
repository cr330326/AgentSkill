# CI/CD Templates for Docker Deployment

## GitHub Actions

### Build, Push, and Deploy via SSH

```yaml
# .github/workflows/deploy.yml
name: Build and Deploy

on:
  push:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    outputs:
      image_tag: ${{ steps.meta.outputs.tags }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix=
            type=raw,value=latest

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest

    steps:
      - name: Checkout (for compose file)
        uses: actions/checkout@v4

      - name: Copy compose file to server
        uses: appleboy/scp-action@v0.1.7
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.DEPLOY_SSH_KEY }}
          source: "compose.yml,.env.production"
          target: "/opt/app"

      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.DEPLOY_SSH_KEY }}
          script: |
            cd /opt/app
            export IMAGE_TAG=${{ github.sha }}
            docker compose pull
            docker compose up -d --remove-orphans
            docker image prune -f
```

### Build and Deploy with docker compose build on server

```yaml
# .github/workflows/deploy-compose.yml
name: Deploy with Compose

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.DEPLOY_SSH_KEY }}
          script: |
            cd /opt/app
            git pull origin main
            docker compose build --no-cache
            docker compose up -d --remove-orphans
            docker image prune -f
            # Verify deployment
            sleep 10
            docker compose ps
            docker compose logs --tail=20 app
```

### Required GitHub Secrets

Set these in your repository Settings > Secrets and variables > Actions:

| Secret | Description |
|--------|-------------|
| `DEPLOY_HOST` | Server IP or hostname |
| `DEPLOY_USER` | SSH username |
| `DEPLOY_SSH_KEY` | Private SSH key for deployment |

If using a container registry other than GHCR:

| Secret | Description |
|--------|-------------|
| `REGISTRY_USERNAME` | Container registry username |
| `REGISTRY_PASSWORD` | Container registry password |

---

## GitLab CI

### Build, Push, and Deploy

```yaml
# .gitlab-ci.yml
stages:
  - build
  - deploy

variables:
  DOCKER_TLS_CERTDIR: "/certs"
  IMAGE_TAG: $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA
  IMAGE_LATEST: $CI_REGISTRY_IMAGE:latest

build:
  stage: build
  image: docker:24
  services:
    - docker:24-dind
  before_script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    - docker build --cache-from $IMAGE_LATEST -t $IMAGE_TAG -t $IMAGE_LATEST .
    - docker push $IMAGE_TAG
    - docker push $IMAGE_LATEST
  only:
    - main

deploy:
  stage: deploy
  image: alpine:3.19
  before_script:
    - apk add --no-cache openssh-client
    - eval $(ssh-agent -s)
    - echo "$DEPLOY_SSH_KEY" | ssh-add -
    - mkdir -p ~/.ssh
    - echo "$SSH_KNOWN_HOSTS" >> ~/.ssh/known_hosts
  script:
    - |
      ssh $DEPLOY_USER@$DEPLOY_HOST << 'EOF'
        cd /opt/app
        export IMAGE_TAG=${CI_COMMIT_SHORT_SHA}
        docker compose pull
        docker compose up -d --remove-orphans
        docker image prune -f
      EOF
  only:
    - main
  environment:
    name: production
    url: https://example.com
```

### Required GitLab CI/CD Variables

Set these in Settings > CI/CD > Variables:

| Variable | Description | Protected | Masked |
|----------|-------------|-----------|--------|
| `DEPLOY_HOST` | Server IP or hostname | Yes | No |
| `DEPLOY_USER` | SSH username | Yes | No |
| `DEPLOY_SSH_KEY` | Private SSH key (File type) | Yes | Yes |
| `SSH_KNOWN_HOSTS` | Output of `ssh-keyscan $DEPLOY_HOST` | Yes | No |

---

## Rollback Strategy

Both pipelines support rollback by redeploying a previous image tag:

```bash
# On the server, roll back to a specific commit SHA
cd /opt/app
export IMAGE_TAG=<previous-commit-sha>
docker compose up -d
```

Or re-run a previous successful pipeline in the CI/CD interface.
