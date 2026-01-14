#!/bin/bash
#
# Reset Admin Password Script
#
# Usage: sudo ./reset_password.sh
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "\n${BLUE}================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root (use sudo)"
    exit 1
fi

print_header "Reset Admin Password"

# Check if container is running
if ! docker ps | grep -q groupdelivery-backend; then
    print_error "Backend container is not running"
    print_warning "Start the containers with: docker compose -f docker-compose.prod.yml up -d"
    exit 1
fi

# Prompt for username
read -p "Enter username: " USERNAME
if [ -z "$USERNAME" ]; then
    print_error "Username is required"
    exit 1
fi

# Prompt for new password
while true; do
    read -s -p "Enter new password: " PASSWORD
    echo
    read -s -p "Confirm new password: " PASSWORD_CONFIRM
    echo

    if [ "$PASSWORD" = "$PASSWORD_CONFIRM" ]; then
        if [ ${#PASSWORD} -lt 8 ]; then
            print_error "Password must be at least 8 characters"
            continue
        fi
        break
    else
        print_error "Passwords do not match"
    fi
done

# Reset the password
print_warning "Resetting password..."
if docker exec groupdelivery-backend python /app/reset_admin_password.py "$USERNAME" "$PASSWORD"; then
    echo
    print_success "Password reset complete!"
else
    echo
    print_error "Failed to reset password"
    exit 1
fi
