#!/bin/bash
# Setup nginx configuration for Group Delivery app

set -e

echo "Setting up nginx configuration for Group Delivery..."

# Backup current config
sudo cp /etc/nginx/sites-available/otp /etc/nginx/sites-available/otp.backup.$(date +%Y%m%d_%H%M%S)

# Add the delivery API location block before the root location
sudo sed -i '/# Proxy frontend to port 9967/i \    # Group Delivery API - proxy to FastAPI backend on port 8000\n    location /delivery/api {\n        rewrite ^/delivery/api/(.*)$ /api/$1 break;\n        proxy_pass http://localhost:8000;\n        proxy_http_version 1.1;\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n        proxy_set_header X-Forwarded-Proto $scheme;\n\n        # CORS headers\n        add_header '"'"'Access-Control-Allow-Origin'"'"' '"'"'*'"'"' always;\n        add_header '"'"'Access-Control-Allow-Methods'"'"' '"'"'GET, POST, PUT, DELETE, OPTIONS, PATCH'"'"' always;\n        add_header '"'"'Access-Control-Allow-Headers'"'"' '"'"'Content-Type, Authorization, X-Requested-With'"'"' always;\n\n        # Handle preflight\n        if ($request_method = '"'"'OPTIONS'"'"') {\n            return 204;\n        }\n    }\n\n' /etc/nginx/sites-available/otp

# Test nginx configuration
echo "Testing nginx configuration..."
sudo nginx -t

# Reload nginx
echo "Reloading nginx..."
sudo systemctl reload nginx

echo "✓ nginx configuration updated successfully!"
echo ""
echo "Your Group Delivery API is now available at:"
echo "  https://tre.hopto.org:9966/delivery/api/"
echo ""
echo "Example test:"
echo "  curl https://tre.hopto.org:9966/delivery/api/addresses"
