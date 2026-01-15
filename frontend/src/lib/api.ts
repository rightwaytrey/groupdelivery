import axios from 'axios';
import type {
  Address, AddressCreate, Driver, DriverCreate, DriverAvailability, AvailabilityCreate,
  DeliveryDay, Route, OptimizationRequest, OptimizationResult
} from '../types';

// Use environment variable or default to nginx proxy path
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to all requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Address API
export const addressApi = {
  list: async (): Promise<Address[]> => {
    const response = await api.get('/addresses');
    return response.data;
  },

  get: async (id: number): Promise<Address> => {
    const response = await api.get(`/addresses/${id}`);
    return response.data;
  },

  create: async (data: AddressCreate): Promise<Address> => {
    const response = await api.post('/addresses', data);
    return response.data;
  },

  update: async (id: number, data: Partial<AddressCreate>): Promise<Address> => {
    const response = await api.put(`/addresses/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/addresses/${id}`);
  },

  deleteAll: async (): Promise<void> => {
    await api.delete('/addresses');
  },

  importCsv: async (file: File): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/addresses/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};

// Driver API
export const driverApi = {
  list: async (): Promise<Driver[]> => {
    const response = await api.get('/drivers');
    return response.data;
  },

  get: async (id: number): Promise<Driver> => {
    const response = await api.get(`/drivers/${id}`);
    return response.data;
  },

  create: async (data: DriverCreate): Promise<Driver> => {
    const response = await api.post('/drivers', data);
    return response.data;
  },

  update: async (id: number, data: Partial<DriverCreate>): Promise<Driver> => {
    const response = await api.put(`/drivers/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/drivers/${id}`);
  },

  deleteAll: async (): Promise<void> => {
    await api.delete('/drivers');
  },

  getAvailability: async (driverId: number): Promise<DriverAvailability[]> => {
    const response = await api.get(`/drivers/${driverId}`);
    return response.data.availability_slots || [];
  },

  addAvailability: async (data: AvailabilityCreate): Promise<DriverAvailability> => {
    const response = await api.post('/drivers/availability', data);
    return response.data;
  },

  getAvailableDrivers: async (date: string): Promise<any[]> => {
    const response = await api.get('/drivers/available', {
      params: { target_date: date },
    });
    return response.data;
  },

  importCsv: async (file: File): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/drivers/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};

// Optimization API
export const optimizationApi = {
  optimize: async (data: OptimizationRequest): Promise<OptimizationResult> => {
    const response = await api.post('/optimize', data);
    return response.data;
  },

  listDeliveryDays: async (): Promise<DeliveryDay[]> => {
    const response = await api.get('/optimize/delivery-days');
    return response.data;
  },

  getDeliveryDay: async (date: string): Promise<DeliveryDay> => {
    const response = await api.get(`/optimize/delivery-days/${date}`);
    return response.data;
  },

  getRoutes: async (deliveryDayId: number): Promise<Route[]> => {
    const response = await api.get(`/optimize/routes/${deliveryDayId}`);
    return response.data;
  },

  deleteDeliveryDay: async (deliveryDayId: number): Promise<void> => {
    await api.delete(`/optimize/delivery-days/${deliveryDayId}`);
  },
};

export default api;
