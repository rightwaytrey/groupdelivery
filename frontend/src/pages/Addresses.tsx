import { useState, useEffect } from 'react';
import { addressApi } from '../lib/api';
import AddressForm from '../components/AddressForm';
import type { Address } from '../types';

export default function Addresses() {
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [showCsvImport, setShowCsvImport] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [editingAddress, setEditingAddress] = useState<Address | null>(null);

  useEffect(() => {
    loadAddresses();
  }, []);

  const loadAddresses = async () => {
    try {
      setLoading(true);
      const data = await addressApi.list();
      setAddresses(data);
    } catch (err) {
      setError('Failed to load addresses');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSuccess = async () => {
    setShowForm(false);
    setEditingAddress(null);
    await loadAddresses();
  };

  const handleEdit = (address: Address) => {
    setEditingAddress(address);
    setShowForm(true);
    setShowCsvImport(false);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this address?')) return;

    try {
      await addressApi.delete(id);
      await loadAddresses();
    } catch (err) {
      console.error('Failed to delete:', err);
      alert('Failed to delete address');
    }
  };

  const handleDeleteAll = async () => {
    if (!confirm(`Are you sure you want to delete all ${addresses.length} addresses? This action cannot be undone.`)) return;

    try {
      await addressApi.deleteAll();
      await loadAddresses();
    } catch (err) {
      console.error('Failed to delete all addresses:', err);
      alert('Failed to delete all addresses');
    }
  };

  const handleCsvUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError(null);
    setUploadSuccess(null);

    try {
      const result = await addressApi.importCsv(file);
      setUploadSuccess(`Successfully imported ${result.imported} addresses. ${result.failed} failed.`);
      setShowCsvImport(false);
      await loadAddresses();

      // Reset file input
      event.target.value = '';
    } catch (err: any) {
      console.error('Failed to upload CSV:', err);
      setError(err.response?.data?.detail || 'Failed to upload CSV file');
    } finally {
      setUploading(false);
    }
  };

  const downloadSampleCsv = () => {
    const csv = `street,city,state,postal_code,country,recipient_name,phone,notes,service_time_minutes
123 Main St,Springfield,IL,62701,USA,John Doe,555-1234,Leave at door,5
456 Oak Ave,Portland,OR,97201,USA,Jane Smith,555-5678,Ring bell,10`;

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'sample_addresses.csv';
    a.click();
    window.URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-500">Loading addresses...</div>
      </div>
    );
  }

  return (
    <div className="px-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-start gap-4 sm:w-fit">
        <div className="flex-shrink-0">
          <h1 className="text-2xl font-semibold text-gray-900">Delivery Addresses</h1>
          <p className="mt-2 text-sm text-gray-700">
            Manage your delivery locations. Addresses are automatically geocoded.
          </p>
        </div>
        <div className="flex gap-3 flex-shrink-0">
          {addresses.length > 0 && (
            <>
              <button
                type="button"
                onClick={handleDeleteAll}
                className="inline-flex items-center justify-center rounded-md border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-700 shadow-sm hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
              >
                <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Delete All
              </button>
              <div className="border-l border-gray-300"></div>
            </>
          )}
          <button
            type="button"
            onClick={() => {
              setShowCsvImport(!showCsvImport);
              setShowForm(false);
            }}
            className="inline-flex items-center justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
          >
            <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            {showCsvImport ? 'Cancel' : 'Import CSV'}
          </button>
          <button
            type="button"
            onClick={() => {
              if (showForm && !editingAddress) {
                setShowForm(false);
              } else {
                setEditingAddress(null);
                setShowForm(true);
                setShowCsvImport(false);
              }
            }}
            className="inline-flex items-center justify-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 sm:w-auto"
          >
            {showForm && !editingAddress ? 'Cancel' : 'Add Address'}
          </button>
        </div>
      </div>

      {error && (
        <div className="mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {uploadSuccess && (
        <div className="mt-4 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
          {uploadSuccess}
        </div>
      )}

      {showCsvImport && (
        <div className="mt-6 bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Import Addresses from CSV</h3>

          <div className="mb-4">
            <p className="text-sm text-gray-600 mb-2">
              Upload a CSV file with the following columns:
            </p>
            <div className="bg-gray-50 rounded p-3 mb-3">
              <code className="text-xs text-gray-800">
                street, city, state, postal_code, country, recipient_name, phone, notes, service_time_minutes
              </code>
            </div>
            <p className="text-sm text-gray-600 mb-3">
              <strong>Required:</strong> street, city
              <br />
              <strong>Optional:</strong> All other fields (country defaults to USA, service_time_minutes defaults to 5)
            </p>
            <button
              type="button"
              onClick={downloadSampleCsv}
              className="text-sm text-indigo-600 hover:text-indigo-500 underline"
            >
              Download sample CSV template
            </button>
          </div>

          <div className="mt-4">
            <label className="block">
              <span className="sr-only">Choose CSV file</span>
              <input
                type="file"
                accept=".csv"
                onChange={handleCsvUpload}
                disabled={uploading}
                className="block w-full text-sm text-gray-500
                  file:mr-4 file:py-2 file:px-4
                  file:rounded-md file:border-0
                  file:text-sm file:font-semibold
                  file:bg-indigo-50 file:text-indigo-700
                  hover:file:bg-indigo-100
                  disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </label>
            {uploading && (
              <p className="mt-2 text-sm text-gray-500">
                Uploading and geocoding addresses...
              </p>
            )}
          </div>

          <div className="mt-4 text-sm text-gray-500">
            <p>
              <strong>Note:</strong> Addresses will be automatically geocoded after import.
              This may take a few moments depending on the number of addresses.
            </p>
          </div>
        </div>
      )}

      {showForm && (
        <div className="mt-6">
          <AddressForm
            onSuccess={handleSuccess}
            onCancel={() => {
              setShowForm(false);
              setEditingAddress(null);
            }}
            address={editingAddress ?? undefined}
          />
        </div>
      )}

      <div className="mt-8 flex flex-col">
        <div className="-my-2 -mx-4 overflow-x-auto sm:-mx-6 lg:-mx-8">
          <div className="inline-block min-w-full py-2 align-middle md:px-6 lg:px-8">
            <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded-lg">
              <table className="min-w-full divide-y divide-gray-300">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                      Address
                    </th>
                    <th className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                      Recipient
                    </th>
                    <th className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                      Phone
                    </th>
                    <th className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                      Delivery Window
                    </th>
                    <th className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900">
                      Status
                    </th>
                    <th className="relative py-3.5 pl-3 pr-4 sm:pr-6">
                      <span className="sr-only">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white">
                  {addresses.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-3 py-4 text-sm text-gray-500 text-center">
                        No addresses found. Add your first address to get started.
                      </td>
                    </tr>
                  ) : (
                    addresses.map((address) => (
                      <tr key={address.id}>
                        <td className="whitespace-nowrap px-3 py-4 text-sm">
                          <div className="font-medium text-gray-900">{address.street}</div>
                          <div className="text-gray-500">
                            {address.city}, {address.state} {address.postal_code}
                          </div>
                        </td>
                        <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                          {address.recipient_name || '-'}
                        </td>
                        <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                          {address.phone || '-'}
                        </td>
                        <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                          {address.preferred_time_start && address.preferred_time_end
                            ? `${address.preferred_time_start} - ${address.preferred_time_end}`
                            : address.preferred_time_start
                            ? `After ${address.preferred_time_start}`
                            : address.preferred_time_end
                            ? `Before ${address.preferred_time_end}`
                            : 'Any time'}
                        </td>
                        <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-500">
                          <span
                            className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${
                              address.geocode_status === 'success'
                                ? 'bg-green-100 text-green-800'
                                : address.geocode_status === 'pending'
                                ? 'bg-yellow-100 text-yellow-800'
                                : 'bg-red-100 text-red-800'
                            }`}
                          >
                            {address.geocode_status}
                          </span>
                        </td>
                        <td className="relative whitespace-nowrap py-4 pl-3 pr-4 text-right text-sm font-medium sm:pr-6">
                          <button
                            onClick={() => handleEdit(address)}
                            className="text-indigo-600 hover:text-indigo-900"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleDelete(address.id)}
                            className="text-red-600 hover:text-red-900 ml-4"
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
