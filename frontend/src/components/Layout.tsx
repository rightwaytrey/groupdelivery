import { Link, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm">
        <div className="max-w-5xl mx-auto px-8 py-2">
          {/* Top row - Logo and Logout */}
          <div className="flex justify-between items-center mb-2">
            <h1 className="text-lg font-bold text-gray-900">Group Delivery</h1>
            <button
              onClick={handleLogout}
              className="px-4 py-2 text-sm font-bold text-white bg-red-600 rounded hover:bg-red-700"
            >
              Logout
            </button>
          </div>

          {/* Navigation buttons - always visible, stacked on mobile */}
          <div className="grid grid-cols-2 md:flex md:flex-wrap gap-2">
            <Link
              to="/"
              className="px-4 py-3 text-center text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700"
            >
              Dashboard
            </Link>
            <Link
              to="/addresses"
              className="px-4 py-3 text-center text-sm font-medium text-white bg-green-600 rounded hover:bg-green-700"
            >
              Addresses
            </Link>
            <Link
              to="/drivers"
              className="px-4 py-3 text-center text-sm font-medium text-white bg-purple-600 rounded hover:bg-purple-700"
            >
              Drivers
            </Link>
            <Link
              to="/routes"
              className="px-4 py-3 text-center text-sm font-medium text-white bg-orange-600 rounded hover:bg-orange-700"
            >
              Routes
            </Link>
            <Link
              to="/map"
              className="px-4 py-3 text-center text-sm font-medium text-white bg-teal-600 rounded hover:bg-teal-700"
            >
              Map
            </Link>
          </div>

          {/* Username */}
          <div className="mt-2 text-xs text-gray-600 text-center">
            {user?.username}
          </div>
        </div>
      </nav>

      <main className="max-w-5xl mx-auto px-8 py-4">
        <Outlet />
      </main>
    </div>
  );
}
