# Group Delivery Route Optimizer

A web application for volunteer-based delivery route optimization using the Vehicle Routing Problem (VRP) approach.

## Features

- Address management with automatic geocoding
- CSV bulk import for addresses
- Volunteer driver management with availability tracking
- Route optimization using OR-Tools
- Interactive map visualization with Leaflet
- Free routing via OpenStreetMap/OSRM

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React + Vite + TypeScript
- **Database**: SQLite
- **VRP Solver**: Google OR-Tools
- **Geocoding**: Nominatim (OpenStreetMap)
- **Routing**: OSRM
- **Map**: Leaflet + OpenStreetMap tiles
- **Deployment**: Docker + Docker Compose + Caddy (automatic HTTPS)

## Quick Deploy to Linux VPS

Deploy the entire application with automatic HTTPS in one command:

```bash
# Clone the repository
git clone <repository-url>
cd morevpsdelivery

# Run the deployment script
sudo ./deploy.sh
```

The script will:
1. Install Docker automatically if not present
2. Prompt for your domain name
3. Prompt for admin username, email, and password
4. Generate secure configuration
5. Deploy the application with automatic SSL via Caddy
6. Create your admin user

**Prerequisites:**
- Fresh Ubuntu/Debian Linux VPS
- Root or sudo access
- Domain name pointed to your server's IP address

**After deployment:**
- Access your app at `https://yourdomain.com`
- API docs at `https://yourdomain.com/api/docs`
- Login with your admin credentials

### Managing Your Deployment

```bash
# View logs
docker compose -f docker-compose.prod.yml logs -f

# Restart services
docker compose -f docker-compose.prod.yml restart

# Stop services
docker compose -f docker-compose.prod.yml down

# Update and restart
docker compose -f docker-compose.prod.yml up -d --build
```

## Local Development Setup

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Local Development URLs:**
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- API documentation: `http://localhost:8000/docs`

Start the frontend:

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Project Structure

```
groupdelivery/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Configuration
│   │   ├── database.py          # Database setup
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── routers/             # API endpoints
│   │   └── services/            # Business logic
│   └── requirements.txt
├── frontend/
│   ├── src/
│   └── package.json
└── data/
    └── delivery.db              # SQLite database
```

## API Endpoints

### Addresses

- `POST /api/addresses` - Create address (auto-geocodes)
- `GET /api/addresses` - List addresses
- `GET /api/addresses/{id}` - Get single address
- `PUT /api/addresses/{id}` - Update address
- `DELETE /api/addresses/{id}` - Delete address
- `POST /api/addresses/import` - Import from CSV
- `POST /api/addresses/geocode/{id}` - Re-geocode address

## CSV Import Format

The CSV file should have the following columns:

**Required:**
- `street` - Street address
- `city` - City name

**Optional:**
- `state` - State/province
- `postal_code` - Postal/ZIP code
- `country` - Country (defaults to USA)
- `recipient_name` - Recipient name
- `phone` - Phone number
- `notes` - Delivery notes
- `service_time_minutes` - Time at stop (default: 5)
- `preferred_time_start` - Preferred start time (HH:MM)
- `preferred_time_end` - Preferred end time (HH:MM)

## Development Status

**Phase 1: Backend Foundation** ✅ COMPLETE
- FastAPI project setup
- Address management with CRUD
- Geocoding service (Nominatim)
- CSV import with validation

**Phase 2: Driver Management** ✅ COMPLETE
- Driver CRUD endpoints
- Availability tracking by date/time
- Query available drivers for specific dates
- Bulk availability creation

**Phase 3: Deployment Simplified** ✅ COMPLETE
- One-command deployment script
- Automatic SSL with Caddy
- Docker Compose production setup
- Admin user creation

**Phase 4-6**: In Progress
- Route optimization (OR-Tools + OSRM)
- React frontend with map
- Full UI with route visualization

## License

MIT
