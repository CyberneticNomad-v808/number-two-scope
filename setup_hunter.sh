#!/bin/bash
# Setup script for SpiderFoot API Key Hunter

set -e

echo "🔥 Setting up SpiderFoot API Key Hunter 🔥"
echo "=========================================="

# Install Playwright
echo "📦 Installing Playwright..."
pip install playwright

# Install browsers
echo "🌐 Installing Chromium browser..."
playwright install chromium

# Make script executable
chmod +x api_key_hunter.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "Usage:"
echo "  Start hunting (High priority): ./api_key_hunter.py --priority High"
echo "  Check status:                 ./api_key_hunter.py --status"
echo "  Export keys (JSON):           ./api_key_hunter.py --export json"
echo "  Export keys (.env):           ./api_key_hunter.py --export env"
echo ""
