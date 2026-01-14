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

L.Marker.prototype.options.icon = DefaultIcon;

interface RouteMapProps {
  routes: Route[];
  addresses: Address[];
  drivers: Driver[];
  height?: string;
}

// Component to fit bounds when routes change
function FitBounds({ routes }: { routes: Route[] }) {
  const map = useMap();

  useEffect(() => {
    if (routes.length > 0) {
      const allCoordinates: [number, number][] = [];

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

      if (allCoordinates.length > 0) {
        const bounds = L.latLngBounds(allCoordinates);
        map.fitBounds(bounds, { padding: [50, 50] });
      }
    }
  }, [routes, map]);

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

        {/* Fit bounds to show all routes */}
        <FitBounds routes={routes} />
      </MapContainer>
    </div>
  );
}
