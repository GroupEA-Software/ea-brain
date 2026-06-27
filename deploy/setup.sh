#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# EA-Brain — Digital Brain :: Debian/Ubuntu Production Setup
# =============================================================================
# Usage:
#   sudo bash setup.sh               # fresh install
#   sudo bash setup.sh --update      # update code + rebuild
#   sudo bash setup.sh --status      # check service status
# =============================================================================

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BAUL_USER="${BAUL_USER:-ea-brain}"
BAUL_GROUP="${BAUL_GROUP:-ea-brain}"
BAUL_PORT="${BAUL_PORT:-3000}"
BAUL_HOST="${BAUL_HOST:-0.0.0.0}"
BAUL_ENV="${BAUL_ENV:-production}"
SERVICE_NAME="ea-brain"
VENV_DIR="$REPO_DIR/.venv"
FRONTEND_DIR="$REPO_DIR/frontend"
SYSTEMD_FILE="/etc/systemd/system/$SERVICE_NAME.service"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${CYAN}[EA-Brain]${NC} $*"; }
ok()   { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*"; exit 1; }

# -- Detect OS -----------------------------------------------------------------
OS="$(grep -oP '^ID=\K.*' /etc/os-release 2>/dev/null || echo 'debian')"
VERSION="$(grep -oP '^VERSION_ID=\K.*' /etc/os-release 2>/dev/null || echo '12')"
log "Detected: $OS $VERSION"

# -- Help ----------------------------------------------------------------------
if [[ "${1:-}" == "--help" ]]; then
  echo "EA-Brain Server Setup"
  echo "  sudo bash setup.sh           Full install"
  echo "  sudo bash setup.sh --update  Pull changes, rebuild frontend, restart"
  echo "  sudo bash setup.sh --status  Service status"
  echo "  sudo bash setup.sh --logs    Tail service logs"
  exit 0
fi

if [[ "${1:-}" == "--status" ]]; then
  systemctl status "$SERVICE_NAME" --no-pager || true
  echo "---"
  echo "Port: $BAUL_PORT"
  echo "User: $BAUL_USER"
  echo "Repo: $REPO_DIR"
  exit 0
fi

if [[ "${1:-}" == "--logs" ]]; then
  journalctl -u "$SERVICE_NAME" -f --no-hostname -o cat
  exit 0
fi

# -- Update mode ---------------------------------------------------------------
if [[ "${1:-}" == "--update" ]]; then
  log "Update mode: pulling changes and rebuilding..."
  cd "$REPO_DIR"
  git pull --ff-only 2>/dev/null || warn "Not a git repo or pull failed — skipping"

  source "$VENV_DIR/bin/activate"
  pip install --quiet -r "$REPO_DIR/requirements.txt" 2>/dev/null

  cd "$FRONTEND_DIR"
  if command -v npm &>/dev/null; then
    npm install --silent 2>/dev/null
    npm run build 2>/dev/null
    ok "Frontend rebuilt"
  fi

  log "Restarting service..."
  systemctl restart "$SERVICE_NAME"
  ok "Update complete — service restarted"
  exit 0
fi

# =============================================================================
# 1. System Dependencies
# =============================================================================
log "Installing system packages..."
export DEBIAN_FRONTEND=noninteractive

apt-get update -qq
apt-get install -y -qq \
  git curl wget gnupg \
  python3 python3-pip python3-venv python3-dev \
  build-essential \
  ffmpeg \
  nginx \
  postgresql postgresql-client \
  redis-server \
  nodejs npm \
  || warn "Some packages may have failed — check above"

if ! command -v node &>/dev/null; then
  warn "Node.js not found, installing via NodeSource..."
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y -qq nodejs
fi

ok "System packages installed"

# =============================================================================
# 2. Create System User
# =============================================================================
if ! id "$BAUL_USER" &>/dev/null; then
  log "Creating system user: $BAUL_USER"
  useradd --system --user-group --home-dir "$REPO_DIR" --no-create-home "$BAUL_USER"
  ok "User $BAUL_USER created"
fi
chown -R "$BAUL_USER:$BAUL_GROUP" "$REPO_DIR" 2>/dev/null || true

# =============================================================================
# 3. Python Virtual Environment
# =============================================================================
log "Setting up Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
  ok "Virtual environment created at $VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install --quiet --upgrade pip setuptools wheel
pip install --quiet -r "$REPO_DIR/requirements.txt"

# Install optional heavy deps (easyocr, sentence-transformers) with a fallback
pip install --quiet sentence-transformers 2>/dev/null || warn "sentence-transformers failed (try --break-system-packages)"
pip install --quiet faiss-cpu 2>/dev/null || warn "faiss-cpu failed — install manually: pip install faiss-cpu"
pip install --quiet easyocr 2>/dev/null || warn "easyocr failed — image OCR disabled"
pip install --quiet google-generativeai 2>/dev/null || warn "google-generativeai failed — Gemini fallback disabled"
pip install --quiet pypdf python-docx python-pptx beautifulsoup4 lxml 2>/dev/null || true
pip install --quiet markitdown 2>/dev/null || true
pip install --quiet ddgs 2>/dev/null || true

ok "Python dependencies installed"

# =============================================================================
# 4. PostgreSQL Database Setup
# =============================================================================
log "Configuring PostgreSQL..."
if systemctl is-active --quiet postgresql; then
  su - postgres -c "psql -tc \"SELECT 1 FROM pg_roles WHERE rolname='$BAUL_USER'\" | grep -q 1" 2>/dev/null \
    || su - postgres -c "psql -c \"CREATE ROLE $BAUL_USER LOGIN PASSWORD 'changeme_baul_$(date +%s)';\"" 2>/dev/null \
    && ok "PostgreSQL role $BAUL_USER created" \
    || warn "PostgreSQL role setup skipped (not running)"
else
  warn "PostgreSQL not running — skipping database setup"
  warn "Start manually: sudo systemctl start postgresql"
fi

# =============================================================================
# 5. Environment Configuration
# =============================================================================
ENV_FILE="$REPO_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
  log "Creating .env from template..."
  if [ -f "$REPO_DIR/deploy/.env.production" ]; then
    cp "$REPO_DIR/deploy/.env.production" "$ENV_FILE"
    ok ".env created from template — EDIT IT: nano $ENV_FILE"
  else
    cat > "$ENV_FILE" <<-EOF
# EA-Brain Production Configuration
# Get free API keys at:
#   OpenCode: https://opencode.ai/zen
#   Groq:    https://console.groq.com
#   Gemini:  https://aistudio.google.com

OPENCODE_API_KEY=
OPENCODE_MODEL=deepseek-v4-flash-free

GROQ_API_KEY=
GROQ_MODEL=llama-3.1-8b-instant

GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash

BRAIN_PATH=$REPO_DIR/brain
CONNECTOR_INTERVAL=300
EVOLVER_INTERVAL=600
CONNECTOR_THRESHOLD=0.60
EOF
    warn ".env created — YOU MUST EDIT IT: nano $ENV_FILE"
  fi
else
  ok ".env already exists"
fi
chown "$BAUL_USER:$BAUL_GROUP" "$ENV_FILE"
chmod 600 "$ENV_FILE"

# =============================================================================
# 6. Frontend Build
# =============================================================================
log "Building frontend..."
cd "$FRONTEND_DIR"
if [ -f "package.json" ]; then
  npm install --silent 2>/dev/null || npm install
  npm run build 2>/dev/null || { warn "Frontend build failed — check npm"; }
  ok "Frontend built"
else
  err "No package.json found in $FRONTEND_DIR"
fi

# =============================================================================
# 6.5. Migrate from old baul.service (if present)
# =============================================================================
if systemctl is-active --quiet baul.service 2>/dev/null; then
  log "Detected old baul.service — migrating to ea-brain.service..."
  systemctl stop baul.service
  systemctl disable baul.service
  rm -f /etc/systemd/system/baul.service
  systemctl daemon-reload
  ok "baul.service stopped, disabled, and removed"
fi

# =============================================================================
# 7. Systemd Service
# =============================================================================
log "Installing systemd service..."
if [ -f "$SYSTEMD_FILE" ]; then
  ok "Service file already exists — overwriting"
fi

cat > "$SYSTEMD_FILE" <<-SERVICE
[Unit]
Description=EA-Brain — Digital Brain
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=$BAUL_USER
Group=$BAUL_GROUP
WorkingDirectory=$REPO_DIR
Environment=PATH=$VENV_DIR/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
EnvironmentFile=$ENV_FILE
ExecStart=$VENV_DIR/bin/uvicorn backend.main:app \\
  --host $BAUL_HOST \\
  --port $BAUL_PORT \\
  --workers 2 \\
  --log-level info
Restart=always
RestartSec=5
StartLimitInterval=60
StartLimitBurst=3

# Security hardening
NoNewPrivileges=yes
ProtectSystem=full
ProtectHome=no
PrivateTmp=yes
ReadWritePaths=$REPO_DIR/brain
ReadWritePaths=$REPO_DIR/.env

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable "$SERVICE_NAME" 2>/dev/null || true
ok "Systemd service installed: $SERVICE_NAME"

# =============================================================================
# 8. Nginx Reverse Proxy (optional)
# =============================================================================
NGINX_CONF="/etc/nginx/sites-available/$SERVICE_NAME"
if [ ! -f "$NGINX_CONF" ] && command -v nginx &>/dev/null; then
  log "Creating nginx configuration..."
  cat > "$NGINX_CONF" <<-NGINX
server {
    listen 80;
    server_name _;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:$BAUL_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }

    location /ws/chat {
        proxy_pass http://127.0.0.1:$BAUL_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 86400s;
    }

    # Uploaded images — serve directly with cache
    location /api/images/ {
        alias $REPO_DIR/brain/baul/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
NGINX
  ln -sf "$NGINX_CONF" "/etc/nginx/sites-enabled/$SERVICE_NAME" 2>/dev/null || true
  nginx -t 2>/dev/null && systemctl reload nginx && ok "Nginx configured" || warn "Nginx config test failed — check manually"
fi

# =============================================================================
# 9. Start Service
# =============================================================================
log "Starting service..."
systemctl start "$SERVICE_NAME" 2>/dev/null || warn "Service failed to start — check: journalctl -u $SERVICE_NAME -n 20"

# =============================================================================
# 10. Summary
# =============================================================================
echo ""
echo "============================================================================="
echo -e "  ${GREEN}EA-Brain — Digital Brain${NC}"
echo "============================================================================="
echo ""
echo "  Service:   sudo systemctl status $SERVICE_NAME"
echo "  Logs:      journalctl -u $SERVICE_NAME -f"
echo "  Restart:   sudo systemctl restart $SERVICE_NAME"
echo "  Stop:      sudo systemctl stop $SERVICE_NAME"
echo ""
echo "  URL:       http://$(hostname -I 2>/dev/null | awk '{print $1}'):$BAUL_PORT"
echo "  Config:    nano $ENV_FILE"
echo "  Brain:     $REPO_DIR/brain/"
echo ""
echo "  Update:    sudo bash $REPO_DIR/deploy/setup.sh --update"
echo ""

if [ ! -f "$ENV_FILE" ] || grep -q "OPENCODE_API_KEY=\|GROQ_API_KEY=\|GEMINI_API_KEY=" "$ENV_FILE" 2>/dev/null; then
  warn " ⚠  You need to configure API keys!"
  echo "     Edit: nano $ENV_FILE"
  echo ""
  echo "     Get free keys at:"
  echo "       OpenCode Zen: https://opencode.ai/zen"
  echo "       Groq:         https://console.groq.com"
  echo "       Gemini:       https://aistudio.google.com"
  echo "     Then: sudo systemctl restart $SERVICE_NAME"
  echo ""
fi
