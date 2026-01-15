import { useState, useEffect, type FormEvent } from 'react';
import { driverApi } from '../lib/api';
import type { Driver, DriverCreate } from '../types';
import AddressAutocomplete from './AddressAutocomplete';

interface DriverFormProps {
  onSuccess: () => void;
  onCancel: () => void;
  driver?: Driver;
}

export default function DriverForm({ onSuccess, onCancel, driver }: DriverFormProps) {
  const isEditing = !!driver;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [formData, setFormData] = useState<DriverCreate>({
    name: driver?.name ?? '',
    email: driver?.email ?? '',
    phone: driver?.phone ?? '',
    vehicle_type: driver?.vehicle_type ?? '',
    home_address: driver?.home_address ?? '',
  });

  // Update form data when driver prop changes
  useEffect(() => {
    if (driver) {
      setFormData({
        name: driver.name,
        email: driver.email ?? '',
        phone: driver.phone ?? '',
        vehicle_type: driver.vehicle_type ?? '',
        home_address: driver.home_address ?? '',
      });
    } else {
      setFormData({
        name: '',
        email: '',
        phone: '',
        vehicle_type: '',
        home_address: '',
      });
    }
  }, [driver]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setWarning(null);

    try {
      // Convert empty strings to undefined for optional fields
      const submitData = {
        ...formData,
        email: formData.email || undefined,
        phone: formData.phone || undefined,
        vehicle_type: formData.vehicle_type || undefined,
        home_address: formData.home_address || undefined,
      };

      let result;
      if (isEditing && driver) {
        result = await driverApi.update(driver.id, submitData);
      } else {
        result = await driverApi.create(submitData);
      }

      // Check if there's a warning in the response
      if (result.warning) {
        setWarning(result.warning);
        // Don't call onSuccess yet - let user see the warning
      } else {
        onSuccess();
      }
    } catch (err: any) {
      console.error(`Failed to ${isEditing ? 'update' : 'create'} driver:`, err);
      setError(err.response?.data?.detail || `Failed to ${isEditing ? 'update' : 'create'} driver`);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field: keyof DriverCreate, value: string | number) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <div className="bg-white shadow rounded-lg p-6 mb-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">{isEditing ? 'Edit Driver' : 'Add New Driver'}</h3>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {warning && (
        <div className="mb-4 bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded">
          <div className="flex items-start">
            <svg className="h-5 w-5 text-yellow-600 mt-0.5 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <div className="flex-1">
              <p className="font-medium">Warning</p>
              <p className="text-sm mt-1">{warning}</p>
              <button
                type="button"
                onClick={onSuccess}
                className="mt-3 text-sm font-medium text-yellow-900 hover:text-yellow-700 underline"
              >
                Continue anyway
              </button>
            </div>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700">
              Driver Name *
            </label>
            <input
              type="text"
              id="name"
              required
              value={formData.name}
              onChange={(e) => handleChange('name', e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
            />
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700">
              Email
            </label>
            <input
              type="email"
              id="email"
              value={formData.email}
              onChange={(e) => handleChange('email', e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
            />
          </div>

          <div>
            <label htmlFor="phone" className="block text-sm font-medium text-gray-700">
              Phone
            </label>
            <input
              type="tel"
              id="phone"
              value={formData.phone}
              onChange={(e) => handleChange('phone', e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
            />
          </div>

          <div className="sm:col-span-2">
            <label htmlFor="vehicle_type" className="block text-sm font-medium text-gray-700">
              Vehicle Type
            </label>
            <input
              type="text"
              id="vehicle_type"
              value={formData.vehicle_type}
              onChange={(e) => handleChange('vehicle_type', e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
              placeholder="e.g., Sedan, SUV, Van"
            />
          </div>

          <div className="sm:col-span-2">
            <AddressAutocomplete
              id="home_address"
              label="Home Address"
              initialValue={formData.home_address}
              onSelectString={(displayName) => handleChange('home_address', displayName)}
              placeholder="Start typing to search for home address..."
            />
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="inline-flex justify-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50"
          >
            {loading ? (isEditing ? 'Saving...' : 'Creating...') : (isEditing ? 'Save Changes' : 'Create Driver')}
          </button>
        </div>
      </form>

      <div className="mt-4 text-sm text-gray-500">
        <p>* Required fields. {isEditing ? 'Home address changes will trigger re-geocoding.' : 'Home address will be automatically geocoded if provided.'}</p>
      </div>
    </div>
  );
}
