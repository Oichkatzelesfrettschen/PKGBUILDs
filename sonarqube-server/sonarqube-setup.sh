#!/bin/sh
set -eu

# SonarQube Server Setup Script
# Initializes Podman container, persistent volumes, and systemd service

SONARQUBE_DATA_DIR="/var/lib/sonarqube"
SONARQUBE_CONFIG_DIR="${HOME}/.config/sonarqube"
SONARQUBE_PORT=9000

echo "=========================================="
echo "SonarQube Server Setup"
echo "=========================================="
echo

# Check Podman availability
if ! command -v podman > /dev/null 2>&1; then
    echo "ERROR: Podman is not installed or not in PATH"
    echo "Install with: sudo pacman -S podman"
    exit 1
fi

# Create configuration directory
echo "Creating configuration directory: ${SONARQUBE_CONFIG_DIR}"
mkdir -p "${SONARQUBE_CONFIG_DIR}"

# Create default environment file if not present
if [ ! -f "${SONARQUBE_CONFIG_DIR}/sonarqube.env" ]; then
    cat > "${SONARQUBE_CONFIG_DIR}/sonarqube.env" << 'EOF'
# SonarQube Server Environment Configuration
SONARQUBE_IMAGE=sonarqube:latest
SONARQUBE_CONTAINER_NAME=sonarqube
SONARQUBE_PORT=9000
SONARQUBE_MEMORY_LIMIT=2g
SONARQUBE_CPUS_LIMIT=2
EOF
    echo "  Created: ${SONARQUBE_CONFIG_DIR}/sonarqube.env"
fi

# Create persistent data directories
echo "Creating persistent data directories..."
mkdir -p "${SONARQUBE_DATA_DIR}/postgresql"
mkdir -p "${SONARQUBE_DATA_DIR}/sonarqube"
mkdir -p "${SONARQUBE_DATA_DIR}/extensions"
mkdir -p "${SONARQUBE_DATA_DIR}/logs"
chmod 755 "${SONARQUBE_DATA_DIR}"
echo "  Created: ${SONARQUBE_DATA_DIR}"

# Pull Podman image
echo
echo "Pulling SonarQube image via Podman (this may take 1-2 minutes)..."
podman pull sonarqube:latest

# Start container for initial setup
echo
echo "Starting SonarQube container for initialization..."
podman run -d \
  --name sonarqube \
  --rm \
  --memory 2g \
  --cpus 2 \
  -p "${SONARQUBE_PORT}:9000" \
  -p 9092:9092 \
  -v "${SONARQUBE_DATA_DIR}/postgresql:/var/lib/postgresql" \
  -v "${SONARQUBE_DATA_DIR}/sonarqube:/opt/sonarqube/data" \
  -v "${SONARQUBE_DATA_DIR}/extensions:/opt/sonarqube/extensions" \
  -v "${SONARQUBE_DATA_DIR}/logs:/opt/sonarqube/logs" \
  -e SONAR_ES_BOOTSTRAP_CHECKS_DISABLED=true \
  -e SONAR_TELEMETRY_ENABLE=false \
  sonarqube:latest

echo "  Container started. Waiting for health check..."
echo

# Wait for SonarQube to be ready
TIMEOUT=120
ELAPSED=0
while [ "${ELAPSED}" -lt "${TIMEOUT}" ]; do
    if curl -s "http://localhost:${SONARQUBE_PORT}/api/system/health" | grep -q '"status":"UP"'; then
        echo "SonarQube is ready"
        break
    fi
    echo "  Waiting for SonarQube to start... (${ELAPSED}/${TIMEOUT} seconds)"
    sleep 5
    ELAPSED=$((ELAPSED + 5))
done

if [ "${ELAPSED}" -ge "${TIMEOUT}" ]; then
    echo "WARNING: SonarQube did not respond within timeout"
    echo "Check logs with: podman logs sonarqube"
fi

# Enable systemd user service
echo
echo "Enabling systemd user service..."
systemctl --user daemon-reload
systemctl --user enable sonarqube-server.service 2>/dev/null || echo "  (Non-critical: systemd user service may require manual setup)"

echo
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo
echo "NEXT STEPS:"
echo "1. Open browser: http://localhost:${SONARQUBE_PORT}"
echo "2. Login with: admin / admin (change immediately)"
echo "3. Generate authentication token:"
echo "   - Administration -> Security -> Users"
echo "   - Generate token for sonar-scanner"
echo
echo "4. Configure sonar-scanner:"
echo "   export SONAR_HOST_URL=http://localhost:${SONARQUBE_PORT}"
echo "   export SONAR_TOKEN=<token>"
echo
echo "5. Analyze project:"
echo "   cd /path/to/project"
echo "   sonar-scanner"
echo
echo "MANAGE SERVICE:"
echo "  Start:   systemctl --user start sonarqube-server"
echo "  Stop:    systemctl --user stop sonarqube-server"
echo "  Status:  systemctl --user status sonarqube-server"
echo "  Logs:    podman logs sonarqube"
echo
echo "DATA LOCATION: ${SONARQUBE_DATA_DIR}"
echo "CONFIG: ${SONARQUBE_CONFIG_DIR}"
echo
