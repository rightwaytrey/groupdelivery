import { useState, type FormEvent } from 'react';
import { addressApi } from '../lib/api';
import type { Address, AddressCreate } from '../types';

interface AddressFormProps {
  onSuccess: () => void;
  onCancel: () => void;
  address?: Address;
}

export default function AddressForm({ onSuccess, onCancel, address }: AddressFormProps) {
  const isEditing = !!address;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<AddressCreate>({
    street: address?.street ?? '',
    city: address?.city ?? '',
    state: address?.state ?? '',
    postal_code: address?.postal_code ?? '',
    country: address?.country ?? 'USA',
    recipient_name: address?.recipient_name ?? '',
    phone: address?.phone ?? '',
    notes: address?.notes ?? '',
    service_time_minutes: address?.service_time_minutes ?? 5,
    preferred_time_start: address?.preferred_time_start ?? '',
    preferred_time_end: address?.preferred_time_end ?? '',
  });

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (isEditing && address) {
        await addressApi.update(address.id, formData);
      } else {
        await addressApi.create(formData);
      }
      onSuccess();
    } catch (err: any) {
      console.error(`Failed to ${isEditing ? 'update' : 'create'} address:`, err);
      setError(err.response?.data?.detail || `Failed to ${isEditing ? 'update' : 'create'} address`);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field: keyof AddressCreate, value: string | number) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <div className="bg-white shadow rounded-lg p-6 mb-6">
      <h3 className="text-lg font-medium text-gray-900 mb-4">{isEditing ? 'Edit Address' : 'Add New Address'}</h3>

      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <label htmlFor="street" className="block text-sm font-medium text-gray-700">
              Street Address *
            </label>
            <input
              type="text"
              id="street"
              required
              value={formData.street}
              onChange={(e) => handleChange('street', e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
            />
          </div>

          <div>
            <label htmlFor="city" className="block text-sm font-medium text-gray-700">
              City *
            </label>
            <input
              type="text"
              id="city"
              required
              value={formData.city}
              onChange={(e) => handleChange('city', e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
            />
          </div>

          <div>
            <label htmlFor="state" className="block text-sm font-medium text-gray-700">
              State
            </label>
            <input
              type="text"
              id="state"
              value={formData.state}
              onChange={(e) => handleChange('state', e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
            />
          </div>

          <div>
            <label htmlFor="postal_code" className="block text-sm font-medium text-gray-700">
              Postal Code
            </label>
            <input
              type="text"
              id="postal_code"
              value={formData.postal_code}
              onChange={(e) => handleChange('postal_code', e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
            />
          </div>

          <div>
            <label htmlFor="country" className="block text-sm font-medium text-gray-700">
              Country
            </label>
            <input
              type="text"
              id="country"
              value={formData.country}
              onChange={(e) => handleChange('country', e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
            />
          </div>

          <div>
            <label htmlFor="recipient_name" className="block text-sm font-medium text-gray-700">
              Recipient Name
            </label>
            <input
              type="text"
              id="recipient_name"
              value={formData.recipient_name}
              onChange={(e) => handleChange('recipient_name', e.target.value)}
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

          <div>
            <label htmlFor="service_time" className="block text-sm font-medium text-gray-700">
              Service Time (minutes)
            </label>
            <input
              type="number"
              id="service_time"
              min="1"
              max="60"
              value={formData.service_time_minutes}
              onChange={(e) => handleChange('service_time_minutes', parseInt(e.target.value))}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
            />
          </div>

          <div>
            <label htmlFor="preferred_time_start" className="block text-sm font-medium text-gray-700">
              No Deliveries Before:
            </label>
            <input
              type="time"
              id="preferred_time_start"
              value={formData.preferred_time_start}
              onChange={(e) => handleChange('preferred_time_start', e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
            />
          </div>

          <div>
            <label htmlFor="preferred_time_end" className="block text-sm font-medium text-gray-700">
              No Deliveries After:
            </label>
            <input
              type="time"
              id="preferred_time_end"
              value={formData.preferred_time_end}
              onChange={(e) => handleChange('preferred_time_end', e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
            />
          </div>

          <div className="sm:col-span-2">
            <label htmlFor="notes" className="block text-sm font-medium text-gray-700">
              Delivery Notes
            </label>
            <textarea
              id="notes"
              rows={3}
              value={formData.notes}
              onChange={(e) => handleChange('notes', e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
              placeholder="E.g., Leave at door, Ring bell twice, etc."
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
            {loading ? (isEditing ? 'Saving...' : 'Creating...') : (isEditing ? 'Save Changes' : 'Create Address')}
          </button>
        </div>
      </form>

      <div className="mt-4 text-sm text-gray-500">
        <p>* Required fields. {isEditing ? 'Address changes will trigger re-geocoding.' : 'Address will be automatically geocoded.'}</p>
      </div>
    </div>
  );
}
