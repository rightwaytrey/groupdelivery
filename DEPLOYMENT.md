# Deployment Guide

This guide explains how to deploy the Group Delivery Route Optimization System to a VPS using Docker Compose.

## Prerequisites

- VPS with Ubuntu 20.04+ (or similar Linux distribution)
- Docker installed
- Docker Compose installed
- Domain name (optional, but recommended)
- SSH access to your VPS

## Quick Start

### 1. Install Docker and Docker Compose

```bash
# Update package index
sudo apt update

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group (to run docker without sudo)
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Log out and back in for group changes to take effect
```

### 2. Clone the Repository

```bash
cd /home/yourusername
git clone https://github.com/rightwaytrey/groupdelivery.git
cd groupdelivery
```

### 3. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit the .env file with your settings
nano .env
```

**Important: Change the `SECRET_KEY` to a strong random value:**
```bash
# Generate a secure secret key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Update `.env` with your values:
```env
SECRET_KEY=your-generated-secret-key-here
OSRM_HOST=http://router.project-osrm.org
GEOCODING_PROVIDER=nominatim
GEOCODING_API_KEY=
```

### 4. Build and Start Services

```bash
# Build the Docker images
docker-compose build

# Start the services
docker-compose up -d

# Check the logs
docker-compose logs -f
```

The application should now be running:
- Frontend: http://your-vps-ip
- Backend API: http://your-vps-ip/api

### 5. Initialize the Database

Create the default admin user:

```bash
# Access the backend container
docker-compose exec backend python create_default_admin.py
```

**Default credentials:**
- Username: `admin`
- Password: `admin123`

**⚠️ IMPORTANT: Change the admin password immediately after first login!**

### 6. Configure Domain (Optional but Recommended)

If you have a domain name, you can set up a reverse proxy with SSL:

#### Option A: Using Caddy (Recommended - Automatic SSL)

Create `Caddyfile`:
```caddyfile
yourdomain.com {
    reverse_proxy frontend:80
}
```

Add Caddy to `docker-compose.yml`:
```yaml
  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    networks:
      - groupdelivery-network
```

#### Option B: Using Nginx with Let's Encrypt

Install certbot and configure nginx on the host (see nginx-config-snippet.conf).

## Managing the Application

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Restart Services
```bash
docker-compose restart
```

### Stop Services
```bash
docker-compose stop
```

### Update Application
```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d
```

### Backup Database
```bash
# The database is stored in ./data/groupdelivery.db
cp data/groupdelivery.db data/groupdelivery.db.backup

# Or create a timestamped backup
cp data/groupdelivery.db "data/backup-$(date +%Y%m%d-%H%M%S).db"
```

### View Running Containers
```bash
docker-compose ps
```

### Access Container Shell
```bash
# Backend
docker-compose exec backend bash

# Frontend
docker-compose exec frontend sh
```

## Configuration

### Environment Variables

**Backend (.env or docker-compose.yml):**
- `SECRET_KEY`: JWT secret key (required, must be changed)
- `DATABASE_URL`: Database connection string
- `OSRM_HOST`: OSRM routing service URL
- `GEOCODING_PROVIDER`: Geocoding service (nominatim, google, mapbox)
- `GEOCODING_API_KEY`: API key if using paid geocoding service
- `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT token expiration time

### Custom OSRM Server

If you want to use your own OSRM server for better performance:

```bash
# Add OSRM to docker-compose.yml
  osrm:
    image: osrm/osrm-backend
    restart: unless-stopped
    volumes:
      - ./osrm-data:/data
    command: osrm-routed --algorithm mld /data/minnesota-latest.osrm
    networks:
      - groupdelivery-network
```

Then update `.env`:
```env
OSRM_HOST=http://osrm:5000
```

## Troubleshooting

### Port 80 Already in Use
```bash
# Check what's using port 80
sudo lsof -i :80

# Stop the service or change the port in docker-compose.yml
ports:
  - "8080:80"  # Access via port 8080 instead
```

### Backend Container Keeps Restarting
```bash
# Check logs
docker-compose logs backend

# Common issues:
# - Missing environment variables
# - Database initialization failed
# - Python dependency issues
```

### Frontend Shows Connection Error
- Check that backend is running: `docker-compose ps`
- Verify nginx configuration in frontend/nginx.conf
- Check network connectivity between containers

### Database Locked Error
```bash
# Stop all containers
docker-compose down

# Check for stale lock files
rm -f data/*.db-shm data/*.db-wal

# Restart
docker-compose up -d
```

## Security Recommendations

1. **Change Default Credentials**: Change admin password immediately
2. **Use Strong SECRET_KEY**: Generate with `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`
3. **Enable HTTPS**: Use Caddy or Let's Encrypt for SSL
4. **Firewall**: Configure UFW to only allow ports 80, 443, and 22
5. **Regular Updates**: Keep Docker images and system packages updated
6. **Backup Database**: Regularly backup `data/groupdelivery.db`
7. **Environment Variables**: Never commit `.env` to version control

## Firewall Configuration

```bash
# Install UFW
sudo apt install ufw

# Allow SSH (important - do this first!)
sudo ufw allow 22

# Allow HTTP and HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

## Monitoring

Consider setting up monitoring with:
- **Uptime Kuma**: Simple uptime monitoring
- **Portainer**: Docker container management UI
- **Prometheus + Grafana**: Advanced metrics

## Performance Tuning

For production use with many addresses/drivers:

1. **Increase container resources** in docker-compose.yml:
```yaml
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

2. **Use PostgreSQL** instead of SQLite for better concurrency:
```yaml
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: groupdelivery
      POSTGRES_USER: groupdelivery
      POSTGRES_PASSWORD: changeme
```

3. **Add Redis** for caching:
```yaml
  redis:
    image: redis:7-alpine
```

## Support

For issues or questions:
- GitHub Issues: https://github.com/rightwaytrey/groupdelivery/issues
- Check logs: `docker-compose logs -f`
- Review container status: `docker-compose ps`
