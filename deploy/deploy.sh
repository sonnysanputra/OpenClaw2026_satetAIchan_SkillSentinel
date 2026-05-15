#!/usr/bin/env bash
# Sync OpenClaw skill wrappers from this repo to /usr/lib/node_modules/openclaw/skills/
#
# Usage:   sudo bash deploy/deploy.sh
# Run on the droplet after `git pull` to re-deploy any changed wrappers.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="/usr/lib/node_modules/openclaw/skills"

if [ ! -d "$SKILLS_DIR" ]; then
    echo "ERROR: $SKILLS_DIR does not exist. Is OpenClaw installed?" >&2
    exit 1
fi

for skill_src in "$REPO_DIR"/deploy/skillsentinel-*/; do
    name="$(basename "$skill_src")"
    target="$SKILLS_DIR/$name"
    echo "==> Deploying $name -> $target"
    mkdir -p "$target"
    cp -v "$skill_src"/*.md "$skill_src"/*.py "$target/"
    chmod +x "$target"/*.py
done

echo
echo "Deployment complete. Verify with:"
echo "    openclaw skills check --agent main | grep -i skillsentinel"
echo
echo "Note: if you added/modified skills, you must also clear the agent's"
echo "session cache and restart the gateway so the new skills appear in"
echo "<available_skills>:"
echo
echo "    rm -f /root/.openclaw/agents/main/sessions/*.jsonl*"
echo "    rm -f /root/.openclaw/agents/main/sessions/*.json"
echo "    openclaw gateway restart"
