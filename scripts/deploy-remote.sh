#!/bin/bash
#
# Auto-deploy to production server after git push
# This script is triggered by the 'git pushd' alias
#

set -e

echo "🚀 Deploying to production server..."
echo ""

# Deploy command
ssh more "cd /home/rwt/groupdelivery && \
  echo '📥 Pulling latest changes...' && \
  git pull origin master && \
  echo '' && \
  echo '🐳 Building and restarting containers...' && \
  docker compose -f docker-compose.prod.yml up -d --build && \
  echo '' && \
  echo '✅ Deployment complete!' && \
  echo '' && \
  echo '📊 Container status:' && \
  docker ps --format 'table {{.Names}}\t{{.Status}}'"

echo ""
echo "✨ Production deployment finished!"
echo "🌐 Check: https://morefood.duckdns.org"
