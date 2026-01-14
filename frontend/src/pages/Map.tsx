import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import { addressApi } from '../lib/api';
import type { Address } from '../types';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix for default marker icons in React-Leaflet
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

L.Marker.prototype.options.icon = DefaultIcon;

export default function Map() {
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAddresses();
  }, []);

  const loadAddresses = async () => {
    try {
      const data = await addressApi.list();
      // Filter only geocoded addresses
      const geocoded = data.filter(
        (addr) => addr.latitude !== null && addr.longitude !== null
      );
      setAddresses(geocoded);
    } catch (err) {
      console.error('Failed to load addresses:', err);
    } finally {
      setLoading(false);
    }
  };

  const center: [number, number] = addresses.length > 0
    ? [addresses[0].latitude!, addresses[0].longitude!]
    : [37.7749, -122.4194]; // Default to SF

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <div className="text-gray-500">Loading map...</div>
      </div>
    );
  }

  return (
    <div className="px-4">
      <div className="mb-4">
        <h1 className="text-2xl font-semibold text-gray-900">Delivery Map</h1>
        <p className="mt-2 text-sm text-gray-700">
          View all delivery addresses on the map. {addresses.length} address(es) displayed.
        </p>
      </div>

      <div className="bg-white shadow rounded-lg overflow-hidden" style={{ height: '600px' }}>
        <MapContainer
          center={center}
          zoom={10}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {addresses.map((address) => (
            <Marker
              key={address.id}
              position={[address.latitude!, address.longitude!]}
            >
              <Popup>
                <div className="text-sm">
                  <div className="font-semibold">{address.recipient_name || 'Address'}</div>
                  <div>{address.street}</div>
                  <div>{address.city}, {address.state} {address.postal_code}</div>
                  {address.phone && <div className="mt-1 text-gray-600">{address.phone}</div>}
                  {address.notes && <div className="mt-1 text-gray-500 italic">{address.notes}</div>}
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
}
