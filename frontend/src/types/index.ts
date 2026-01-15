// Address types
export interface Address {
  id: number;
  street: string;
  city: string;
  state: string | null;
  postal_code: string | null;
  country: string;
  recipient_name: string | null;
  phone: string | null;
  notes: string | null;
  service_time_minutes: number;
  preferred_time_start: string | null;
  preferred_time_end: string | null;
  latitude: number | null;
  longitude: number | null;
  geocode_status: string;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface AddressCreate {
  street: string;
  city: string;
  state?: string;
  postal_code?: string;
  country?: string;
  recipient_name?: string;
  phone?: string;
  notes?: string;
  service_time_minutes?: number;
  preferred_time_start?: string;
  preferred_time_end?: string;
}

// Driver types
export interface Driver {
  id: number;
  name: string;
  email: string | null;
  phone: string | null;
  vehicle_type: string | null;
  max_stops: number;
  max_route_duration_minutes: number;
  home_address: string | null;
  home_latitude: number | null;
  home_longitude: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface DriverCreate {
  name: string;
  email?: string;
  phone?: string;
  vehicle_type?: string;
  max_stops?: number;
  max_route_duration_minutes?: number;
  home_address?: string;
}

export interface DriverAvailability {
  id: number;
  driver_id: number;
  date: string;
  start_time: string;
  end_time: string;
  status: 'available' | 'tentative' | 'unavailable';
  created_at: string;
  updated_at: string | null;
}

export interface AvailabilityCreate {
  driver_id: number;
  date: string;
  start_time: string;
  end_time: string;
  status?: 'available' | 'tentative' | 'unavailable';
}

// Route optimization types
export interface DeliveryDay {
  id: number;
  date: string;
  depot_latitude: number | null;
  depot_longitude: number | null;
  depot_address: string | null;
  status: string;
  total_stops: number;
  total_drivers: number;
  total_distance_km: number;
  total_duration_minutes: number;
  created_at: string;
  updated_at: string | null;
}

export interface RouteStop {
  id: number;
  route_id: number;
  address_id: number;
  sequence: number;
  estimated_arrival: string | null;
  estimated_departure: string | null;
  distance_from_previous_km: number;
  duration_from_previous_minutes: number;
  status: string;
  created_at: string;
  updated_at: string | null;
}

export interface Route {
  id: number;
  delivery_day_id: number;
  driver_id: number;
  route_number: number;
  color: string | null;
  total_stops: number;
  total_distance_km: number;
  total_duration_minutes: number;
  route_geometry: string | null;
  start_time: string | null;
  end_time: string | null;
  stops: RouteStop[];
  created_at: string;
  updated_at: string | null;
}

export interface OptimizationRequest {
  date: string;
  address_ids: number[];
  driver_ids: number[];
  depot_latitude?: number;
  depot_longitude?: number;
  depot_address?: string;
  start_time?: string;
  driver_constraints?: Record<number, {
    max_stops?: number;
    max_route_duration_minutes?: number;
    start_time?: string;
    end_at_home?: boolean;
  }>;
  time_limit_seconds?: number;
}

export interface DroppedAddressDetail {
  address_id: number;
  recipient_name: string;
  street: string;
  reason: string;
  time_window: string;
  service_time_minutes: number;
}

export interface OptimizationResult {
  delivery_day_id: number;
  date: string;
  status: string;
  total_routes: number;
  total_stops: number;
  total_distance_km: number;
  total_duration_minutes: number;
  routes: Route[];
  dropped_addresses: number[];
  dropped_address_details?: DroppedAddressDetail[];
  message: string | null;
}
