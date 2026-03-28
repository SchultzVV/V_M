#!/bin/bash
# ============================================================
# Cloudflare Tunnel Manager — Quick Tunnel (account-less)
# Inicia túnel sem usar config persistente (~/.cloudflared/config.yml)
# Isso evita conflitos de configuração
# ============================================================

set -e  # Fail fast

CLOUDFLARED_BIN=$(command -v cloudflared 2>/dev/null || echo /usr/local/bin/cloudflared)
LOG_FILE="${1:-/tmp/cloudflare_tunnel.log}"
TUNNEL_URL="${2:-http://localhost:443}"
MAX_WAIT_SECS="${3:-20}"

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'  # No Color

# ============================================================
# 1. Validate cloudflared is installed
# ============================================================
if [ ! -x "$CLOUDFLARED_BIN" ]; then
    echo -e "${RED}❌ cloudflared não instalado${NC}" >&2
    echo "   Execute: make install-cloudflared" >&2
    exit 1
fi

# ============================================================
# 2. Check if tunnel is already running
# ============================================================
check_tunnel_running() {
    if pgrep -f "cloudflared tunnel" > /dev/null 2>&1; then
        return 0  # tunnel is running
    else
        return 1  # tunnel is not running
    fi
}

# ============================================================
# 3. Start tunnel (if not already running)
# ============================================================
start_tunnel() {
    local tunnel_url="${1:-http://localhost:443}"
    
    echo -e "${YELLOW}🌐 Iniciando túnel Cloudflare para: $tunnel_url${NC}" >&2
    
    # Remove old log
    rm -f "$LOG_FILE"
    
    # Determine protocol
    local protocol="http"
    if [[ "$tunnel_url" == https://* ]]; then
        protocol="https"
    fi
    
    # Start tunnel in background (discard tee stdout to prevent capture)
    # Use minimal flags — avoid TLS verification for HTTP origins
    if [ "$protocol" = "http" ]; then
        # For HTTP origins, no TLS needed
        "$CLOUDFLARED_BIN" tunnel \
            --url "$tunnel_url" \
            --proxy-connect-timeout 60s \
            --proxy-keepalive-timeout 5m \
            --proxy-keepalive-connections 200 \
            --proxy-tcp-keepalive 60s \
            2>&1 | tee "$LOG_FILE" >/dev/null &
    else
        # For HTTPS origins, use --no-tls-verify
        "$CLOUDFLARED_BIN" tunnel \
            --url "$tunnel_url" \
            --no-tls-verify \
            --proxy-connect-timeout 60s \
            --proxy-keepalive-timeout 5m \
            --proxy-keepalive-connections 200 \
            --proxy-tcp-keepalive 60s \
            2>&1 | tee "$LOG_FILE" >/dev/null &
    fi
    
    # Store PID
    TUNNEL_PID=$!
    echo $TUNNEL_PID > "/tmp/cloudflare_tunnel.pid"
}

# ============================================================
# 4. Wait for tunnel URL to be captured
# ============================================================
wait_for_tunnel_url() {
    local max_wait=$1
    local iteration=0
    local cf_url=""
    
    echo -e "${YELLOW}⏳ Aguardando URL do túnel (max ${max_wait}s)...${NC}" >&2
    
    while [ $iteration -lt $max_wait ]; do
        # Try to extract URL from log
        if [ -f "$LOG_FILE" ]; then
            cf_url=$(grep -oP 'https://[a-z0-9\-]+\.trycloudflare\.com' "$LOG_FILE" 2>/dev/null | head -1)
        fi
        
        if [ -n "$cf_url" ]; then
            echo -e "${GREEN}✅ URL capturada: $cf_url${NC}" >&2
            # ONLY the URL to stdout
            echo "$cf_url"
            return 0
        fi
        
        sleep 1
        iteration=$((iteration + 1))
    done
    
    echo -e "${RED}❌ URL não capturada em ${max_wait}s${NC}" >&2
    echo "   Log: cat $LOG_FILE" >&2
    return 1
}

# ============================================================
# Main Logic
# ============================================================
main() {
    # DEBUG: Show received URL
    echo -e "${YELLOW}📍 URL do túnel: $TUNNEL_URL${NC}" >&2
    
    # Always kill old cloudflared to ensure fresh start with new URL
    pkill -f "cloudflared tunnel" || true
    sleep 1
    
    # Start new tunnel with current URL
    start_tunnel "$TUNNEL_URL"
    
    # Wait for URL
    if wait_for_tunnel_url "$MAX_WAIT_SECS"; then
        return 0
    else
        return 1
    fi
}

# Execute
main
