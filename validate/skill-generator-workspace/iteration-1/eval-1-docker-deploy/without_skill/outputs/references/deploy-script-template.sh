#!/usr/bin/env bash
# deploy.sh - Docker Compose deployment helper script
# Usage: ./deploy.sh [command]
#   Commands:
#     deploy   - Build and start all services (default)
#     stop     - Stop all services
#     restart  - Restart all services
#     logs     - Follow logs for all services
#     status   - Show service status
#     update   - Pull latest images and redeploy
#     rollback - Roll back to previous image
#     backup   - Backup database volume
#     clean    - Remove unused Docker resources

set -euo pipefail

# Configuration - override via environment or .env file
COMPOSE_FILE="${COMPOSE_FILE:-compose.yml}"
PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "$0")" && pwd)}"
REMOTE_HOST="${REMOTE_HOST:-}"
REMOTE_USER="${REMOTE_USER:-deploy}"
REMOTE_DIR="${REMOTE_DIR:-/opt/app}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# Check prerequisites
check_prereqs() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Install it first: https://docs.docker.com/get-docker/"
        exit 1
    fi
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose V2 is not available."
        exit 1
    fi
    if [ ! -f "$PROJECT_DIR/$COMPOSE_FILE" ]; then
        log_error "Compose file not found: $PROJECT_DIR/$COMPOSE_FILE"
        exit 1
    fi
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        if [ -f "$PROJECT_DIR/.env.example" ]; then
            log_warn ".env file not found. Copy from .env.example and configure:"
            log_warn "  cp .env.example .env"
            exit 1
        fi
    fi
}

# Deploy locally
deploy() {
    log_info "Building and starting services..."
    docker compose -f "$COMPOSE_FILE" build
    docker compose -f "$COMPOSE_FILE" up -d --remove-orphans
    log_info "Waiting for services to be healthy..."
    sleep 5
    docker compose -f "$COMPOSE_FILE" ps
    log_info "Deployment complete."
}

# Deploy to remote server
deploy_remote() {
    if [ -z "$REMOTE_HOST" ]; then
        log_error "REMOTE_HOST is not set. Set it in .env or environment."
        exit 1
    fi
    log_info "Deploying to ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}..."

    # Sync files to remote
    rsync -avz --delete \
        --exclude='.git' \
        --exclude='node_modules' \
        --exclude='.env' \
        --exclude='backups' \
        "$PROJECT_DIR/" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/"

    # Build and start on remote
    ssh "${REMOTE_USER}@${REMOTE_HOST}" bash -s << 'REMOTE_EOF'
        cd "$REMOTE_DIR"
        docker compose build
        docker compose up -d --remove-orphans
        docker image prune -f
        echo "--- Service Status ---"
        docker compose ps
REMOTE_EOF

    log_info "Remote deployment complete."
}

# Stop services
stop() {
    log_info "Stopping services..."
    docker compose -f "$COMPOSE_FILE" down
    log_info "Services stopped."
}

# Restart services
restart() {
    log_info "Restarting services..."
    docker compose -f "$COMPOSE_FILE" restart
    docker compose -f "$COMPOSE_FILE" ps
}

# Follow logs
logs() {
    local service="${1:-}"
    if [ -n "$service" ]; then
        docker compose -f "$COMPOSE_FILE" logs -f --tail=100 "$service"
    else
        docker compose -f "$COMPOSE_FILE" logs -f --tail=100
    fi
}

# Show status
status() {
    docker compose -f "$COMPOSE_FILE" ps
    echo ""
    log_info "Resource usage:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" \
        $(docker compose -f "$COMPOSE_FILE" ps -q) 2>/dev/null || true
}

# Update (pull and redeploy)
update() {
    log_info "Pulling latest images..."
    docker compose -f "$COMPOSE_FILE" pull
    log_info "Rebuilding and restarting..."
    docker compose -f "$COMPOSE_FILE" up -d --build --remove-orphans
    docker image prune -f
    log_info "Update complete."
}

# Backup database
backup() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    mkdir -p "$BACKUP_DIR"

    # Detect database type from compose file
    if docker compose -f "$COMPOSE_FILE" ps postgres &>/dev/null 2>&1; then
        log_info "Backing up PostgreSQL..."
        docker compose -f "$COMPOSE_FILE" exec -T postgres \
            pg_dumpall -U "${DB_USER:-app}" > "$BACKUP_DIR/postgres_${timestamp}.sql"
        log_info "Backup saved to $BACKUP_DIR/postgres_${timestamp}.sql"
    elif docker compose -f "$COMPOSE_FILE" ps mysql &>/dev/null 2>&1; then
        log_info "Backing up MySQL..."
        docker compose -f "$COMPOSE_FILE" exec -T mysql \
            mysqldump --all-databases -u root -p"${DB_ROOT_PASSWORD}" > "$BACKUP_DIR/mysql_${timestamp}.sql"
        log_info "Backup saved to $BACKUP_DIR/mysql_${timestamp}.sql"
    elif docker compose -f "$COMPOSE_FILE" ps mongo &>/dev/null 2>&1; then
        log_info "Backing up MongoDB..."
        docker compose -f "$COMPOSE_FILE" exec -T mongo \
            mongodump --archive --gzip -u "${MONGO_USER:-admin}" -p "${MONGO_PASSWORD}" \
            > "$BACKUP_DIR/mongo_${timestamp}.gz"
        log_info "Backup saved to $BACKUP_DIR/mongo_${timestamp}.gz"
    else
        log_warn "No recognized database service found."
    fi
}

# Clean up unused resources
clean() {
    log_warn "This will remove unused Docker resources (images, containers, volumes, networks)."
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker system prune -af
        log_info "Cleanup complete."
    else
        log_info "Cancelled."
    fi
}

# Main
cd "$PROJECT_DIR"
check_prereqs

case "${1:-deploy}" in
    deploy)         deploy ;;
    deploy-remote)  deploy_remote ;;
    stop)           stop ;;
    restart)        restart ;;
    logs)           logs "${2:-}" ;;
    status)         status ;;
    update)         update ;;
    backup)         backup ;;
    clean)          clean ;;
    *)
        echo "Usage: $0 {deploy|deploy-remote|stop|restart|logs [service]|status|update|backup|clean}"
        exit 1
        ;;
esac
