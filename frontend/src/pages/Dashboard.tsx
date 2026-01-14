import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { addressApi, driverApi, optimizationApi } from '../lib/api';

export default function Dashboard() {
  const [stats, setStats] = useState({
    totalAddresses: 0,
    geocodedAddresses: 0,
    activeDrivers: 0,
    totalRoutes: 0,
    loading: true,
  });

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const [addresses, drivers, deliveryDays] = await Promise.all([
        addressApi.list(),
        driverApi.list(),
        optimizationApi.listDeliveryDays(),
      ]);

      const geocoded = addresses.filter(addr => addr.latitude && addr.longitude);
      const active = drivers.filter(d => d.is_active);

      setStats({
        totalAddresses: addresses.length,
        geocodedAddresses: geocoded.length,
        activeDrivers: active.length,
        totalRoutes: deliveryDays.length,
        loading: false,
      });
    } catch (err) {
      console.error('Failed to load stats:', err);
      setStats(prev => ({ ...prev, loading: false }));
    }
  };

  return (
    <div className="px-4">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h2>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Total Addresses
                  </dt>
                  <dd className="text-lg font-semibold text-gray-900">
                    {stats.loading ? 'Loading...' : stats.totalAddresses}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
          <div className="bg-gray-50 px-5 py-3">
            <div className="text-sm">
              <Link to="/addresses" className="font-medium text-indigo-600 hover:text-indigo-500">
                View all
              </Link>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Geocoded Addresses
                  </dt>
                  <dd className="text-lg font-semibold text-gray-900">
                    {stats.loading ? 'Loading...' : stats.geocodedAddresses}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
          <div className="bg-gray-50 px-5 py-3">
            <div className="text-sm">
              <span className="text-gray-500">
                Ready for optimization
              </span>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Active Drivers
                  </dt>
                  <dd className="text-lg font-semibold text-gray-900">
                    {stats.loading ? 'Loading...' : stats.activeDrivers}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
          <div className="bg-gray-50 px-5 py-3">
            <div className="text-sm">
              <Link to="/drivers" className="font-medium text-indigo-600 hover:text-indigo-500">
                Manage drivers
              </Link>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                </svg>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Optimized Routes
                  </dt>
                  <dd className="text-lg font-semibold text-gray-900">
                    {stats.loading ? 'Loading...' : stats.totalRoutes}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
          <div className="bg-gray-50 px-5 py-3">
            <div className="text-sm">
              <Link to="/routes" className="font-medium text-indigo-600 hover:text-indigo-500">
                View routes
              </Link>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-8 bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Quick Start</h3>
        <div className="space-y-4">
          <div className="flex items-start">
            <div className="flex items-center justify-center w-8 h-8 rounded-full bg-indigo-100 text-indigo-600 font-semibold text-sm mr-4">
              1
            </div>
            <div className="flex-1">
              <h4 className="text-sm font-medium text-gray-700">Add Delivery Addresses</h4>
              <p className="text-sm text-gray-500 mt-1">
                Start by adding addresses manually or importing them from a CSV file.
              </p>
              <Link to="/addresses" className="text-sm text-indigo-600 hover:text-indigo-500 mt-2 inline-block">
                Go to Addresses →
              </Link>
            </div>
          </div>
          <div className="flex items-start">
            <div className="flex items-center justify-center w-8 h-8 rounded-full bg-indigo-100 text-indigo-600 font-semibold text-sm mr-4">
              2
            </div>
            <div className="flex-1">
              <h4 className="text-sm font-medium text-gray-700">Register Volunteer Drivers</h4>
              <p className="text-sm text-gray-500 mt-1">
                Add your volunteer drivers and their vehicle information.
              </p>
              <Link to="/drivers" className="text-sm text-indigo-600 hover:text-indigo-500 mt-2 inline-block">
                Go to Drivers →
              </Link>
            </div>
          </div>
          <div className="flex items-start">
            <div className="flex items-center justify-center w-8 h-8 rounded-full bg-indigo-100 text-indigo-600 font-semibold text-sm mr-4">
              3
            </div>
            <div className="flex-1">
              <h4 className="text-sm font-medium text-gray-700">Optimize Routes</h4>
              <p className="text-sm text-gray-500 mt-1">
                Use the VRP solver to create efficient delivery routes with estimated arrival times.
              </p>
              <Link to="/routes" className="text-sm text-indigo-600 hover:text-indigo-500 mt-2 inline-block">
                Create Routes →
              </Link>
            </div>
          </div>
        </div>
      </div>

      {stats.totalAddresses === 0 && !stats.loading && (
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-blue-800">
                Get Started
              </h3>
              <div className="mt-2 text-sm text-blue-700">
                <p>
                  You haven't added any addresses yet. Add your first delivery address to get started with route optimization!
                </p>
              </div>
              <div className="mt-4">
                <Link
                  to="/addresses"
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-blue-700 bg-blue-100 hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  Add Address
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
