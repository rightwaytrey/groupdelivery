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

## Setup

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

### Access URLs

**Production (via nginx reverse proxy):**
- API: `https://tre.hopto.org:9966/delivery/api/`
- API Docs: `https://tre.hopto.org:9966/delivery/api/docs` (coming soon)
- Addresses: `https://tre.hopto.org:9966/delivery/api/addresses`
- Drivers: `https://tre.hopto.org:9966/delivery/api/drivers`

**Local Development:**
- API: `http://localhost:8000`
- API documentation: `http://localhost:8000/docs`

### Frontend

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

**Phase 3: Reverse Proxy Setup** ✅ COMPLETE
- nginx configuration on port 9966
- Path-based routing: `/delivery/api/*`
- SSL/HTTPS enabled
- CORS headers configured

**Phase 4-6**: Coming soon
- Route optimization (OR-Tools + OSRM)
- React frontend with map
- Full UI with route visualization

## License

MIT
