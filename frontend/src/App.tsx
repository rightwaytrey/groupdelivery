import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Addresses from './pages/Addresses';
import Drivers from './pages/Drivers';
import RoutesPage from './pages/Routes';
import Map from './pages/Map';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="addresses" element={<Addresses />} />
            <Route path="drivers" element={<Drivers />} />
            <Route path="routes" element={<RoutesPage />} />
            <Route path="map" element={<Map />} />
          </Route>
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
