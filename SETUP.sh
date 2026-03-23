#!/bin/bash
# Setup Claude Agents Orchestrator for a new project

set -e

PROJECT_NAME="${1:-.}"

echo "🚀 Setting up Claude Agents Orchestrator for: $PROJECT_NAME"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Register plugin marketplace in user's global Claude Code settings
register_plugin_marketplace() {
  local settings_file="$HOME/.claude/settings.json"
  local marketplace_name="claude-agents-orchestrator"
  local marketplace_config='{
    "source": {
      "source": "github",
      "repo": "pascalpldev/claude-agents-orchestrator"
    }
  }'

  # Create settings file if it doesn't exist
  if [ ! -f "$settings_file" ]; then
    mkdir -p "$(dirname "$settings_file")"
    echo '{"extraKnownMarketplaces": {}}' > "$settings_file"
  fi

  # Check if marketplace is already registered
  if ! grep -q "\"$marketplace_name\"" "$settings_file" 2>/dev/null; then
    # Use jq to safely merge the marketplace config into settings.json
    jq ".extraKnownMarketplaces[\"$marketplace_name\"] = $marketplace_config" "$settings_file" > "$settings_file.tmp" 2>/dev/null

    if [ $? -eq 0 ]; then
      mv "$settings_file.tmp" "$settings_file"
      echo "✓ Plugin marketplace registered in ~/.claude/settings.json"
    else
      rm -f "$settings_file.tmp"
      echo "⚠ Warning: Could not register plugin marketplace (jq might not be installed)"
    fi
  else
    echo "✓ Plugin marketplace already registered"
  fi
}

# 1. Create GitHub labels
echo -e "${BLUE}Creating GitHub labels...${NC}"
gh label create "to-enrich" --color "e2a5ff" --force 2>/dev/null || true
gh label create "enriching" --color "ffd700" --force 2>/dev/null || true
gh label create "enriched" --color "90ee90" --force 2>/dev/null || true
gh label create "to-dev" --color "87ceeb" --force 2>/dev/null || true
gh label create "dev-in-progress" --color "ff6347" --force 2>/dev/null || true
gh label create "to-test" --color "ffa500" --force 2>/dev/null || true
gh label create "deployed" --color "32cd32" --force 2>/dev/null || true
gh label create "godeploy" --color "9370db" --force 2>/dev/null || true
echo -e "${GREEN}✅ Labels created${NC}"

# 2. Create branches
echo -e "${BLUE}Creating branches...${NC}"
git checkout -b dev 2>/dev/null || git checkout dev
git push -u origin dev 2>/dev/null || echo "Branch dev already exists"
echo -e "${GREEN}✅ Branches ready${NC}"

# 2.5. Register the plugin marketplace
echo -e "${BLUE}Registering plugin marketplace...${NC}"
register_plugin_marketplace
echo -e "${GREEN}✅ Plugin marketplace setup complete${NC}"

# 3. Create cao.config.yml if it doesn't exist
if [ ! -f cao.config.yml ]; then
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
  if [ -f "$SCRIPT_DIR/cao.config.example.yml" ]; then
    cp "$SCRIPT_DIR/cao.config.example.yml" cao.config.yml
    echo -e "${GREEN}✅ cao.config.yml created — edit it to configure your deploy platform${NC}"
  else
    cat > cao.config.yml << 'EOF'
# cao.config.yml — Claude Agents Orchestrator
deploy:
  platform: none      # Options: railway | render | vercel | none
  project: ""
  service: ""
EOF
    echo -e "${GREEN}✅ cao.config.yml created${NC}"
  fi
else
  echo -e "${GREEN}✅ cao.config.yml already exists${NC}"
fi

# 4. Install pre-commit hook
echo -e "${BLUE}Installing pre-commit hook...${NC}"
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit
echo -e "${GREEN}✅ Pre-commit hook installed${NC}"

# 5. Info
echo ""
echo -e "${GREEN}✅ Claude Agents Orchestrator setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Skills are already available globally:"
echo "   - /cao-hello-team-lead"
echo "   - /cao-get-ticket #N"
echo "   - /cao-process-tickets"
echo "   - /cao-show-logs"
echo ""
echo "2. Create your first ticket:"
echo "   gh issue create --title 'Feature: ...' --label 'to-enrich'"
echo ""
echo "3. Start the workflow:"
echo "   /cao-process-tickets"
echo ""
echo "📖 Documentation: see CLAUDE.md in this directory"
