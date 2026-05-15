#!/usr/bin/env bash
# Install + start all SkillSentinel agent bots as systemd services.
#
# Prereqs:
#   - /opt/skillsentinel exists, with .venv set up and discord.py installed
#   - /root/.skillsentinel/bots.env contains the per-bot tokens
#     (export SKILLSENTINEL_BOT_TOKEN_INTAKE=..., etc.) — protected 0600
#
# Usage:  sudo bash deploy/systemd/install-bots.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SYSTEMD_DIR="/etc/systemd/system"

# Materialize bots.env from current shell env if it doesn't exist already.
ENV_FILE="/root/.skillsentinel/bots.env"
if [ ! -f "$ENV_FILE" ]; then
    mkdir -p "$(dirname "$ENV_FILE")"
    : > "$ENV_FILE"
    for agent in INTAKE STATIC SEMANTIC DYNAMIC VERDICT COORDINATOR; do
        var="SKILLSENTINEL_BOT_TOKEN_$agent"
        val="${!var:-}"
        if [ -n "$val" ]; then
            echo "$var=$val" >> "$ENV_FILE"
        fi
    done
    if [ -n "${SKILLSENTINEL_DISCORD_CHANNEL_ID:-}" ]; then
        echo "SKILLSENTINEL_DISCORD_CHANNEL_ID=$SKILLSENTINEL_DISCORD_CHANNEL_ID" >> "$ENV_FILE"
    fi
    if [ -n "${SKILLSENTINEL_DISCORD_WEBHOOK:-}" ]; then
        echo "SKILLSENTINEL_DISCORD_WEBHOOK=$SKILLSENTINEL_DISCORD_WEBHOOK" >> "$ENV_FILE"
    fi
    if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
        echo "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY" >> "$ENV_FILE"
    fi
    chmod 0600 "$ENV_FILE"
    echo "Wrote $ENV_FILE"
fi

# Install the systemd template unit.
cp -v "$REPO_DIR/deploy/systemd/[email protected]" "$SYSTEMD_DIR/[email protected]"
systemctl daemon-reload

# Enable + start one instance per agent.
for agent in intake static semantic dynamic verdict coordinator; do
    systemctl enable "skillsentinel-bot@${agent}.service"
    systemctl restart "skillsentinel-bot@${agent}.service"
    sleep 1
done

echo
echo "Status:"
systemctl --no-pager --type=service | grep skillsentinel-bot || true
echo
echo "Tail logs of all bots with:"
echo "    journalctl -u 'skillsentinel-bot@*' -f -n 50"
