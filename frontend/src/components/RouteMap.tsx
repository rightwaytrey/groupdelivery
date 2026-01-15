import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { Route, Address, Driver } from '../types';

// Fix Leaflet icon issue
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

// Create a custom home icon using SVG
const homeIconSvg = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="32" height="32">
  <path d="M11.47 3.84a.75.75 0 011.06 0l8.69 8.69a.75.75 0 101.06-1.06l-8.689-8.69a2.25 2.25 0 00-3.182 0l-8.69 8.69a.75.75 0 001.061 1.06l8.69-8.69z" />
  <path d="M12 5.432l8.159 8.159c.03.03.06.058.091.086v6.198c0 1.035-.84 1.875-1.875 1.875H15a.75.75 0 01-.75-.75v-4.5a.75.75 0 00-.75-.75h-3a.75.75 0 00-.75.75V21a.75.75 0 01-.75.75H5.625a1.875 1.875 0 01-1.875-1.875v-6.198a2.29 2.29 0 00.091-.086L12 5.43z" />
</svg>
`;

const HomeIcon = L.divIcon({
  html: `<div style="color: #EF4444; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));">${homeIconSvg}</div>`,
  className: 'custom-home-icon',
  iconSize: [32, 32],
  iconAnchor: [16, 32],
  popupAnchor: [0, -32],
});

// Create a depot/warehouse icon
const depotIconSvg = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="32" height="32">
  <path d="M11.47 3.84a.75.75 0 011.06 0l8.69 8.69a.75.75 0 101.06-1.06l-8.689-8.69a2.25 2.25 0 00-3.182 0l-8.69 8.69a.75.75 0 001.061 1.06l8.69-8.69z" />
  <path d="M12 5.432l8.159 8.159c.03.03.06.058.091.086v6.198c0 1.035-.84 1.875-1.875 1.875H15a.75.75 0 01-.75-.75v-4.5a.75.75 0 00-.75-.75h-3a.75.75 0 00-.75.75V21a.75.75 0 01-.75.75H5.625a1.875 1.875 0 01-1.875-1.875v-6.198a2.29 2.29 0 00.091-.086L12 5.43z" />
</svg>
`;

const DepotIcon = L.divIcon({
  html: `<div style="color: #3B82F6; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));">${depotIconSvg}</div>`,
  className: 'custom-depot-icon',
  iconSize: [32, 32],
  iconAnchor: [16, 32],
  popupAnchor: [0, -32],
});

L.Marker.prototype.options.icon = DefaultIcon;

interface RouteMapProps {
  routes: Route[];
  addresses: Address[];
  drivers: Driver[];
  height?: string;
  showDriverHomes?: number[]; // Array of driver IDs to show home markers for
  depotLocation?: { latitude: number; longitude: number; address: string }; // Depot location
}

// Component to fit bounds when routes change
function FitBounds({
  routes,
  drivers,
  showDriverHomes,
  depotLocation
}: {
  routes: Route[];
  drivers: Driver[];
  showDriverHomes?: number[];
  depotLocation?: { latitude: number; longitude: number; address: string };
}) {
  const map = useMap();

  useEffect(() => {
    const allCoordinates: [number, number][] = [];

    if (routes.length > 0) {
      // Fit to routes if they exist
      routes.forEach((route) => {
        if (route.route_geometry) {
          try {
            const geometry = JSON.parse(route.route_geometry);
            if (geometry.coordinates) {
              geometry.coordinates.forEach((coord: [number, number]) => {
                // GeoJSON uses [lon, lat], Leaflet uses [lat, lon]
                allCoordinates.push([coord[1], coord[0]]);
              });
            }
          } catch (e) {
            console.error('Failed to parse route geometry:', e);
          }
        }
      });
    } else if (showDriverHomes && showDriverHomes.length > 0) {
      // Preview mode - fit to depot and selected driver homes
      if (depotLocation) {
        allCoordinates.push([depotLocation.latitude, depotLocation.longitude]);
      }

      showDriverHomes.forEach(driverId => {
        const driver = drivers.find(d => d.id === driverId);
        if (driver && driver.home_latitude && driver.home_longitude) {
          allCoordinates.push([driver.home_latitude, driver.home_longitude]);
        }
      });
    }

    if (allCoordinates.length > 0) {
      const bounds = L.latLngBounds(allCoordinates);
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [routes, drivers, showDriverHomes, depotLocation, map]);

  return null;
}

export default function RouteMap({ routes, addresses, drivers, height = '600px' }: RouteMapProps) {
  const [center] = useState<[number, number]>([37.7749, -122.4194]); // San Francisco default
  const [addressMap, setAddressMap] = useState<Map<number, Address>>(new Map());
  const [driverMap, setDriverMap] = useState<Map<number, Driver>>(new Map());

  useEffect(() => {
    const addrMap = new Map(addresses.map(addr => [addr.id, addr]));
    setAddressMap(addrMap);
  }, [addresses]);

  useEffect(() => {
    const drvMap = new Map(drivers.map(drv => [drv.id, drv]));
    setDriverMap(drvMap);
  }, [drivers]);

  // Parse route geometries into Leaflet-compatible format
  const routePolylines = routes.map((route) => {
    if (!route.route_geometry) return null;

    try {
      const geometry = JSON.parse(route.route_geometry);
      if (geometry.coordinates) {
        // Convert GeoJSON [lon, lat] to Leaflet [lat, lon]
        const positions: [number, number][] = geometry.coordinates.map(
          (coord: [number, number]) => [coord[1], coord[0]]
        );

        return {
          route,
          positions,
          color: route.color || '#3B82F6',
        };
      }
    } catch (e) {
      console.error('Failed to parse route geometry:', e);
    }

    return null;
  }).filter(Boolean);

  return (
    <div style={{ height }}>
      <MapContainer
        center={center}
        zoom={10}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Draw route polylines */}
        {routePolylines.map((routeData, _idx) => {
          if (!routeData) return null;
          const driver = driverMap.get(routeData.route.driver_id);

          return (
            <Polyline
              key={`route-${routeData.route.id}`}
              positions={routeData.positions}
              color={routeData.color}
              weight={4}
              opacity={0.7}
            >
              <Popup>
                <div className="text-sm">
                  <h3 className="font-semibold">Route #{routeData.route.route_number}</h3>
                  <p><strong>Driver:</strong> {driver?.name || 'Unknown'}</p>
                  <p><strong>Stops:</strong> {routeData.route.total_stops}</p>
                  <p><strong>Distance:</strong> {routeData.route.total_distance_km.toFixed(1)} km</p>
                  <p><strong>Duration:</strong> {Math.round(routeData.route.total_duration_minutes)} min</p>
                  <p><strong>Time:</strong> {routeData.route.start_time} - {routeData.route.end_time}</p>
                </div>
              </Popup>
            </Polyline>
          );
        })}

        {/* Draw markers for each stop */}
        {routes.map((route) => {
          const driver = driverMap.get(route.driver_id);
          return route.stops.map((stop, _idx) => {
            const address = addressMap.get(stop.address_id);
            if (!address || !address.latitude || !address.longitude) return null;

            return (
              <Marker
                key={`stop-${stop.id}`}
                position={[address.latitude, address.longitude]}
              >
                <Popup>
                  <div className="text-sm">
                    <h3 className="font-semibold">Stop #{stop.sequence}</h3>
                    <p style={{ color: route.color || '#3B82F6' }} className="font-semibold">
                      Route #{route.route_number} - {driver?.name || 'Unknown'}
                    </p>
                    <p className="text-xs mt-1"><strong>Address:</strong></p>
                    <p className="text-xs">{address.street}</p>
                    <p className="text-xs">{address.city}, {address.state} {address.postal_code}</p>
                    {address.recipient_name && (
                      <p className="text-xs mt-1"><strong>Recipient:</strong> {address.recipient_name}</p>
                    )}
                    <p className="text-xs mt-1">
                      <strong>Arrival:</strong> {stop.estimated_arrival}
                    </p>
                    <p className="text-xs">
                      <strong>Departure:</strong> {stop.estimated_departure}
                    </p>
                  </div>
                </Popup>
              </Marker>
            );
          });
        })}

        {/* Draw home endpoint markers for routes ending at driver's home */}
        {routes.map((route) => {
          const driver = driverMap.get(route.driver_id);
          // Check if driver has home coordinates and route geometry ends near home
          if (!driver || !driver.home_latitude || !driver.home_longitude) return null;

          // Parse route geometry to get the last coordinate (endpoint)
          if (!route.route_geometry) return null;

          try {
            const geometry = JSON.parse(route.route_geometry);
            if (!geometry.coordinates || geometry.coordinates.length === 0) return null;

            // Get last coordinate from route geometry [lon, lat]
            const lastCoord = geometry.coordinates[geometry.coordinates.length - 1];
            const endLat = lastCoord[1];
            const endLon = lastCoord[0];

            // Check if endpoint is close to driver's home (within ~100 meters)
            const latDiff = Math.abs(endLat - driver.home_latitude);
            const lonDiff = Math.abs(endLon - driver.home_longitude);
            const isAtHome = latDiff < 0.001 && lonDiff < 0.001;

            if (!isAtHome) return null;

            return (
              <Marker
                key={`home-${route.id}`}
                position={[driver.home_latitude, driver.home_longitude]}
                icon={HomeIcon}
              >
                <Popup>
                  <div className="text-sm">
                    <h3 className="font-semibold">🏠 Route Endpoint</h3>
                    <p style={{ color: route.color || '#3B82F6' }} className="font-semibold">
                      Route #{route.route_number} - {driver.name}
                    </p>
                    <p className="text-xs mt-1"><strong>Ends at driver's home</strong></p>
                    <p className="text-xs">{driver.home_address || 'Home address'}</p>
                    <p className="text-xs mt-1">
                      <strong>End time:</strong> {route.end_time}
                    </p>
                  </div>
                </Popup>
              </Marker>
            );
          } catch (e) {
            console.error('Failed to parse route geometry for home marker:', e);
            return null;
          }
        })}

        {/* Fit bounds to show all routes */}
        <FitBounds routes={routes} />
      </MapContainer>
    </div>
  );
}
