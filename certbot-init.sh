#!/bin/bash
# Usage: DOMAIN=eroom.example.com EMAIL=admin@example.com ./certbot-init.sh
set -euo pipefail

DOMAIN="${DOMAIN:?set DOMAIN env var}"
EMAIL="${EMAIL:?set EMAIL env var}"

# Create certbot webroot
mkdir -p /var/www/certbot

# Obtain cert
certbot certonly --webroot \
  -w /var/www/certbot \
  -d "$DOMAIN" \
  --email "$EMAIL" \
  --agree-tos \
  --non-interactive

# Reload nginx
nginx -s reload

echo "✅ SSL cert obtained for $DOMAIN"
echo "   Renewal cron: certbot renew --quiet && nginx -s reload"