import { useState, useEffect } from 'react';
import { optimizationApi, addressApi, driverApi } from '../lib/api';
import RouteMap from '../components/RouteMap';
import type { Route, Address, Driver, OptimizationResult, DeliveryDay } from '../types';

export default function Routes() {
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [deliveryDays, setDeliveryDays] = useState<DeliveryDay[]>([]);
  const [selectedDeliveryDayId, setSelectedDeliveryDayId] = useState<number | null>(null);
  const [routes, setRoutes] = useState<Route[]>([]);
  const [loading, setLoading] = useState(true);
  const [optimizing, setOptimizing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  // Form state
  const [selectedDate, setSelectedDate] = useState(() => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    return tomorrow.toISOString().split('T')[0];
  });
  const [selectedAddresses, setSelectedAddresses] = useState<number[]>([]);
  const [selectedDrivers, setSelectedDrivers] = useState<number[]>([]);
  const [startTime, setStartTime] = useState('09:00');
  const [driverConstraints, setDriverConstraints] = useState<Record<number, { max_stops?: number; max_route_duration_minutes?: number }>>({});

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [addrs, drvs, days] = await Promise.all([
        addressApi.list(),
        driverApi.list(),
        optimizationApi.listDeliveryDays(),
      ]);
      setAddresses(addrs);
      setDrivers(drvs);
      setDeliveryDays(days);

      // Auto-select the most recent delivery day if available
      if (days.length > 0 && !selectedDeliveryDayId) {
        const mostRecent = days[0];
        setSelectedDeliveryDayId(mostRecent.id);
        loadRoutes(mostRecent.id);
      }
    } catch (err) {
      console.error('Failed to load data:', err);
      setError('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const loadRoutes = async (deliveryDayId: number) => {
    try {
      const routeData = await optimizationApi.getRoutes(deliveryDayId);
      setRoutes(routeData);
    } catch (err) {
      console.error('Failed to load routes:', err);
      setError('Failed to load routes');
    }
  };

  const handleOptimize = async () => {
    if (selectedAddresses.length === 0) {
      setError('Please select at least one address');
      return;
    }
    if (selectedDrivers.length === 0) {
      setError('Please select at least one driver');
      return;
    }

    setOptimizing(true);
    setError(null);

    // Calculate if we need proportional distribution
    const totalMaxStops = Object.values(driverConstraints).reduce(
      (sum, c) => sum + (c.max_stops || 15), 0
    );

    let finalConstraints = driverConstraints;

    if (selectedAddresses.length < totalMaxStops) {
      // Not enough addresses - distribute proportionally by duration
      const totalDuration = Object.values(driverConstraints).reduce(
        (sum, c) => sum + (c.max_route_duration_minutes || 120), 0
      );

      finalConstraints = {};
      for (const [driverId, constraint] of Object.entries(driverConstraints)) {
        const duration = constraint.max_route_duration_minutes || 120;
        const proportion = duration / totalDuration;
        const proportionalStops = Math.max(1, Math.round(selectedAddresses.length * proportion));

        finalConstraints[parseInt(driverId)] = {
          max_stops: proportionalStops,
          max_route_duration_minutes: duration
        };
      }
    }

    try {
      const result: OptimizationResult = await optimizationApi.optimize({
        date: selectedDate,
        address_ids: selectedAddresses,
        driver_ids: selectedDrivers,
        start_time: startTime,
        driver_constraints: finalConstraints,
        time_limit_seconds: 30,
      });

      // Reload delivery days list
      const days = await optimizationApi.listDeliveryDays();
      setDeliveryDays(days);

      // Set the new delivery day as selected
      setSelectedDeliveryDayId(result.delivery_day_id);
      setRoutes(result.routes);
      setShowForm(false);

      if (result.dropped_addresses.length > 0) {
        setError(`Optimization complete! ${result.dropped_addresses.length} addresses could not be assigned.`);
      }
    } catch (err: any) {
      console.error('Optimization failed:', err);
      setError(err.response?.data?.detail || 'Optimization failed');
    } finally {
      setOptimizing(false);
    }
  };

  const handleDeliveryDayChange = async (deliveryDayId: number) => {
    setSelectedDeliveryDayId(deliveryDayId);
    await loadRoutes(deliveryDayId);
  };

  const handleExportAllRoutes = async () => {
    if (!selectedDeliveryDayId) return;
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/optimize/delivery-days/${selectedDeliveryDayId}/export`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('Export failed');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `delivery-day-${selectedDeliveryDayId}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Export error:', err);
      setError('Failed to export routes');
    }
  };

  const handleDeleteDeliveryDay = async () => {
    if (!selectedDeliveryDayId) return;

    const selectedDay = deliveryDays.find(d => d.id === selectedDeliveryDayId);
    if (!confirm(`Are you sure you want to delete the delivery day for ${selectedDay?.date}? This will delete all routes for this day.`)) {
      return;
    }

    try {
      await optimizationApi.deleteDeliveryDay(selectedDeliveryDayId);

      // Reload delivery days list
      const days = await optimizationApi.listDeliveryDays();
      setDeliveryDays(days);

      // Clear selection and routes
      setSelectedDeliveryDayId(null);
      setRoutes([]);

      // Auto-select the most recent delivery day if available
      if (days.length > 0) {
        const mostRecent = days[0];
        setSelectedDeliveryDayId(mostRecent.id);
        loadRoutes(mostRecent.id);
      }
    } catch (err) {
      console.error('Delete error:', err);
      setError('Failed to delete delivery day');
    }
  };

  const handleExportRoute = async (routeId: number) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/optimize/routes/${routeId}/export`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) throw new Error('Export failed');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `route-${routeId}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Export error:', err);
      setError('Failed to export route');
    }
  };

  const toggleAddressSelection = (addressId: number) => {
    setSelectedAddresses(prev =>
      prev.includes(addressId)
        ? prev.filter(id => id !== addressId)
        : [...prev, addressId]
    );
  };

  const toggleDriverSelection = (driverId: number) => {
    setSelectedDrivers(prev => {
      if (prev.includes(driverId)) {
        // Remove driver and their constraints
        setDriverConstraints(prevConstraints => {
          const newConstraints = { ...prevConstraints };
          delete newConstraints[driverId];
          return newConstraints;
        });
        return prev.filter(id => id !== driverId);
      } else {
        // Add driver with default constraints
        setDriverConstraints(prevConstraints => ({
          ...prevConstraints,
          [driverId]: {
            max_stops: 15,
            max_route_duration_minutes: 120
          }
        }));
        return [...prev, driverId];
      }
    });
  };

  const geocodedAddresses = addresses.filter(addr => addr.latitude && addr.longitude);
  const selectedDeliveryDay = deliveryDays.find(d => d.id === selectedDeliveryDayId);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  return (
    <div className="px-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-start gap-4 sm:w-fit">
        <div className="flex-shrink-0">
          <h1 className="text-2xl font-semibold text-gray-900">Route Optimization</h1>
          <p className="mt-2 text-sm text-gray-700">
            Optimize delivery routes using the Vehicle Routing Problem solver.
          </p>
        </div>
        <div className="flex-shrink-0">
          <button
            type="button"
            onClick={() => setShowForm(!showForm)}
            className="inline-flex items-center justify-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
          >
            {showForm ? 'Cancel' : 'New Optimization'}
          </button>
        </div>
      </div>

      {error && (
        <div className="mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Optimization Form */}
      {showForm && (
        <div className="mt-6 bg-white shadow rounded-lg p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Create Route Optimization</h3>

          {/* Depot Info */}
          <div className="mb-6 bg-blue-50 border border-blue-200 rounded-md p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-blue-700">
                  <span className="font-medium">Route Origin:</span> All routes will start and end at 96 E Wheelock Pkwy, St Paul, MN 55117
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <div>
              <label htmlFor="date" className="block text-sm font-medium text-gray-700">
                Delivery Date *
              </label>
              <input
                type="date"
                id="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
              />
            </div>

            <div>
              <label htmlFor="start_time" className="block text-sm font-medium text-gray-700">
                Start Time
              </label>
              <input
                type="time"
                id="start_time"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
              />
            </div>
          </div>

          {/* Address Selection */}
          <div className="mt-6">
            <h4 className="text-sm font-medium text-gray-900 mb-2">
              Select Addresses ({selectedAddresses.length} selected)
            </h4>
            <div className="border rounded-md p-4 max-h-60 overflow-y-auto">
              {geocodedAddresses.length === 0 ? (
                <p className="text-sm text-gray-500">No geocoded addresses available. Please add addresses with valid coordinates.</p>
              ) : (
                geocodedAddresses.map((addr) => (
                  <label key={addr.id} className="flex items-center py-2 hover:bg-gray-50 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedAddresses.includes(addr.id)}
                      onChange={() => toggleAddressSelection(addr.id)}
                      className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                    />
                    <span className="ml-3 text-sm text-gray-700">
                      {addr.street}, {addr.city} {addr.state}
                      {addr.recipient_name && ` - ${addr.recipient_name}`}
                    </span>
                  </label>
                ))
              )}
            </div>
            <button
              type="button"
              onClick={() => setSelectedAddresses(geocodedAddresses.map(a => a.id))}
              className="mt-2 text-sm text-indigo-600 hover:text-indigo-500"
            >
              Select All
            </button>
            <button
              type="button"
              onClick={() => setSelectedAddresses([])}
              className="mt-2 ml-4 text-sm text-indigo-600 hover:text-indigo-500"
            >
              Clear All
            </button>
          </div>

          {/* Driver Selection */}
          <div className="mt-6">
            <h4 className="text-sm font-medium text-gray-900 mb-2">
              Select Drivers ({selectedDrivers.length} selected)
            </h4>
            <div className="border rounded-md p-4 max-h-96 overflow-y-auto">
              {drivers.length === 0 ? (
                <p className="text-sm text-gray-500">No drivers available. Please add drivers first.</p>
              ) : (
                drivers.filter(d => d.is_active).map((driver) => (
                  <div key={driver.id} className="py-3 border-b last:border-b-0">
                    <label className="flex items-center hover:bg-gray-50 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedDrivers.includes(driver.id)}
                        onChange={() => toggleDriverSelection(driver.id)}
                        className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                      />
                      <span className="ml-3 text-sm font-medium text-gray-700">
                        {driver.name} - {driver.vehicle_type || 'No vehicle'}
                      </span>
                    </label>
                    {selectedDrivers.includes(driver.id) && (
                      <div className="mt-3 ml-7 grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-xs font-medium text-gray-600 mb-1">
                            Max Stops
                          </label>
                          <input
                            type="number"
                            min="1"
                            max="50"
                            value={driverConstraints[driver.id]?.max_stops ?? ''}
                            onChange={(e) => {
                              const value = e.target.value === '' ? undefined : parseInt(e.target.value);
                              setDriverConstraints(prev => ({
                                ...prev,
                                [driver.id]: {
                                  ...prev[driver.id],
                                  max_stops: value
                                }
                              }));
                            }}
                            placeholder="15"
                            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm px-2 py-1 border"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-600 mb-1">
                            Max Route Duration (min)
                          </label>
                          <input
                            type="number"
                            min="60"
                            max="720"
                            value={driverConstraints[driver.id]?.max_route_duration_minutes ?? ''}
                            onChange={(e) => {
                              const value = e.target.value === '' ? undefined : parseInt(e.target.value);
                              setDriverConstraints(prev => ({
                                ...prev,
                                [driver.id]: {
                                  ...prev[driver.id],
                                  max_route_duration_minutes: value
                                }
                              }));
                            }}
                            placeholder="120"
                            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm px-2 py-1 border"
                          />
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
            <button
              type="button"
              onClick={() => {
                const activeDriverIds = drivers.filter(d => d.is_active).map(d => d.id);
                setSelectedDrivers(activeDriverIds);
                // Initialize constraints for all drivers
                const newConstraints: Record<number, { max_stops?: number; max_route_duration_minutes?: number }> = {};
                activeDriverIds.forEach(id => {
                  newConstraints[id] = {
                    max_stops: 15,
                    max_route_duration_minutes: 120
                  };
                });
                setDriverConstraints(newConstraints);
              }}
              className="mt-2 text-sm text-indigo-600 hover:text-indigo-500"
            >
              Select All
            </button>
            <button
              type="button"
              onClick={() => {
                setSelectedDrivers([]);
                setDriverConstraints({});
              }}
              className="mt-2 ml-4 text-sm text-indigo-600 hover:text-indigo-500"
            >
              Clear All
            </button>
          </div>

          <div className="mt-6 flex justify-end">
            <button
              type="button"
              onClick={handleOptimize}
              disabled={optimizing || selectedAddresses.length === 0 || selectedDrivers.length === 0}
              className="inline-flex justify-center rounded-md border border-transparent bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50"
            >
              {optimizing ? 'Optimizing...' : 'Run Optimization'}
            </button>
          </div>
        </div>
      )}

      {/* Delivery Day Selector */}
      {deliveryDays.length > 0 && !showForm && (
        <div className="mt-6">
          <label htmlFor="delivery_day" className="block text-sm font-medium text-gray-700 mb-2">
            View Delivery Day
          </label>
          <select
            id="delivery_day"
            value={selectedDeliveryDayId || ''}
            onChange={(e) => handleDeliveryDayChange(parseInt(e.target.value))}
            className="block w-full sm:w-64 rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm px-3 py-2 border"
          >
            <option value="">Select a delivery day...</option>
            {deliveryDays.map((day) => (
              <option key={day.id} value={day.id}>
                {day.date} - {day.total_drivers} routes, {day.total_stops} stops
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Route Summary */}
      {selectedDeliveryDay && routes.length > 0 && !showForm && (
        <div className="mt-6 bg-white shadow rounded-lg p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium text-gray-900">Route Summary</h3>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleDeleteDeliveryDay}
                className="inline-flex items-center px-3 py-2 border border-red-300 shadow-sm text-sm leading-4 font-medium rounded-md text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
              >
                <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Delete
              </button>
              <button
                type="button"
                onClick={handleExportAllRoutes}
                className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                <svg className="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Export All Routes
              </button>
            </div>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-gray-500">Total Routes</p>
              <p className="text-2xl font-semibold text-gray-900">{selectedDeliveryDay.total_drivers}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Total Stops</p>
              <p className="text-2xl font-semibold text-gray-900">{selectedDeliveryDay.total_stops}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Total Distance</p>
              <p className="text-2xl font-semibold text-gray-900">
                {selectedDeliveryDay.total_distance_km.toFixed(1)} km
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Total Duration</p>
              <p className="text-2xl font-semibold text-gray-900">
                {Math.round(selectedDeliveryDay.total_duration_minutes)} min
              </p>
            </div>
          </div>

          {/* Route Details */}
          <div className="mt-6">
            <h4 className="text-sm font-medium text-gray-900 mb-3">Route Details</h4>
            <div className="space-y-3">
              {routes.map((route) => {
                const driver = drivers.find(d => d.id === route.driver_id);
                return (
                  <div key={route.id} className="border rounded-md p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        <div
                          className="w-4 h-4 rounded-full mr-3"
                          style={{ backgroundColor: route.color || '#3B82F6' }}
                        ></div>
                        <div>
                          <p className="font-medium text-gray-900">
                            Route #{route.route_number} - {driver?.name || 'Unknown'}
                          </p>
                          <p className="text-sm text-gray-500">
                            {route.total_stops} stops • {route.total_distance_km.toFixed(1)} km • {Math.round(route.total_duration_minutes)} min
                          </p>
                          <p className="text-sm text-gray-500">
                            {route.start_time} - {route.end_time}
                          </p>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleExportRoute(route.id)}
                        className="inline-flex items-center px-3 py-1.5 border border-gray-300 shadow-sm text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                      >
                        <svg className="h-3 w-3 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        Export CSV
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Map */}
      {routes.length > 0 && !showForm && (
        <div className="mt-6">
          <RouteMap
            routes={routes}
            addresses={addresses}
            drivers={drivers}
            height="700px"
          />
        </div>
      )}

      {deliveryDays.length === 0 && !showForm && (
        <div className="mt-6 text-center py-12 bg-gray-50 rounded-lg">
          <p className="text-gray-500">No delivery days found. Click "New Optimization" to create your first route optimization.</p>
        </div>
      )}
    </div>
  );
}
