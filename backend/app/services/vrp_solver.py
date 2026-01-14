"""
Vehicle Routing Problem solver using Google OR-Tools.
Handles route optimization with time windows and driver constraints.
"""
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp


class VRPSolver:
    def __init__(
        self,
        distance_matrix: List[List[float]],
        duration_matrix: List[List[float]],
        num_vehicles: int,
        depot_index: int = 0
    ):
        """
        Initialize VRP solver.

        Args:
            distance_matrix: NxN matrix of distances in km
            duration_matrix: NxN matrix of durations in minutes
            num_vehicles: Number of available vehicles/drivers
            depot_index: Index of depot location (default: 0)
        """
        self.distance_matrix = distance_matrix
        self.duration_matrix = duration_matrix
        self.num_vehicles = num_vehicles
        self.depot_index = depot_index
        self.num_locations = len(distance_matrix)

        # Default constraints
        self.service_times = [5] * self.num_locations  # 5 minutes per stop
        self.service_times[depot_index] = 0  # No service time at depot

        # Time windows (in minutes from start) - default to 8 hours
        self.time_windows = [(0, 480)] * self.num_locations

        # Max route duration per vehicle (4 hours = 240 minutes default)
        self.max_route_durations = [240] * num_vehicles

        # Vehicle capacities (max stops per vehicle)
        self.vehicle_capacities = [15] * num_vehicles

    def set_service_times(self, service_times: List[int]):
        """Set service time (in minutes) for each location."""
        self.service_times = service_times

    def set_time_windows(self, time_windows: List[Tuple[int, int]]):
        """
        Set time windows for each location.

        Args:
            time_windows: List of (start, end) tuples in minutes from start
        """
        self.time_windows = time_windows

    def set_vehicle_capacities(self, capacities: List[int]):
        """Set max stops capacity for each vehicle."""
        self.vehicle_capacities = capacities

    def set_max_route_duration(self, minutes: int):
        """Set maximum duration for all routes in minutes."""
        self.max_route_durations = [minutes] * self.num_vehicles

    def set_max_route_durations(self, durations: List[int]):
        """Set maximum duration for each vehicle in minutes."""
        self.max_route_durations = durations

    def solve(self, time_limit_seconds: int = 30) -> Optional[Dict]:
        """
        Solve the VRP and return optimized routes.

        Args:
            time_limit_seconds: Max time for solver to run

        Returns:
            Dictionary with route solutions, or None if no solution found
        """
        # Create the routing index manager
        manager = pywrapcp.RoutingIndexManager(
            self.num_locations,
            self.num_vehicles,
            self.depot_index
        )

        # Create routing model
        routing = pywrapcp.RoutingModel(manager)

        # Create distance callback
        def distance_callback(from_index, to_index):
            """Returns the distance between two nodes."""
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(self.distance_matrix[from_node][to_node] * 1000)  # Convert to meters

        distance_callback_index = routing.RegisterTransitCallback(distance_callback)

        # Define cost of each arc (distance-based)
        routing.SetArcCostEvaluatorOfAllVehicles(distance_callback_index)

        # Add time dimension (duration-based)
        def time_callback(from_index, to_index):
            """Returns the travel time + service time."""
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            travel_time = int(self.duration_matrix[from_node][to_node])
            service_time = self.service_times[from_node]
            return travel_time + service_time

        time_callback_index = routing.RegisterTransitCallback(time_callback)

        # Use the maximum of all vehicle durations for the dimension capacity
        max_duration_overall = max(self.max_route_durations)

        routing.AddDimension(
            time_callback_index,
            30,  # Allow waiting time (slack)
            max_duration_overall,  # Maximum time per vehicle (use max of all)
            False,  # Don't force start cumul to zero
            'Time'
        )

        time_dimension = routing.GetDimensionOrDie('Time')

        # Set per-vehicle max route duration constraints
        for vehicle_id in range(self.num_vehicles):
            index = routing.End(vehicle_id)
            time_dimension.CumulVar(index).SetMax(self.max_route_durations[vehicle_id])

        # Add time windows constraints
        for location_idx in range(self.num_locations):
            if location_idx == self.depot_index:
                continue
            index = manager.NodeToIndex(location_idx)
            time_dimension.CumulVar(index).SetRange(
                self.time_windows[location_idx][0],
                self.time_windows[location_idx][1]
            )

        # Add time windows for depot
        depot_idx = manager.NodeToIndex(self.depot_index)
        time_dimension.CumulVar(depot_idx).SetRange(
            self.time_windows[self.depot_index][0],
            self.time_windows[self.depot_index][1]
        )

        # Instantiate route start and end times to produce feasible times
        for i in range(self.num_vehicles):
            routing.AddVariableMinimizedByFinalizer(
                time_dimension.CumulVar(routing.Start(i))
            )
            routing.AddVariableMinimizedByFinalizer(
                time_dimension.CumulVar(routing.End(i))
            )

        # Add capacity constraint (max stops per vehicle)
        def demand_callback(from_index):
            """Returns the demand (1 stop per location)."""
            from_node = manager.IndexToNode(from_index)
            return 1 if from_node != self.depot_index else 0

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)

        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # null capacity slack
            self.vehicle_capacities,  # vehicle maximum capacities
            True,  # start cumul to zero
            'Capacity'
        )

        # Allow dropping nodes (with high penalty)
        penalty = 100000
        for node in range(1, self.num_locations):
            routing.AddDisjunction([manager.NodeToIndex(node)], penalty)

        # Set search parameters
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = time_limit_seconds
        search_parameters.log_search = False

        # Solve the problem
        solution = routing.SolveWithParameters(search_parameters)

        if not solution:
            return None

        # Extract solution
        return self._extract_solution(manager, routing, solution)

    def _extract_solution(self, manager, routing, solution) -> Dict:
        """Extract routes from the solution."""
        routes = []
        total_distance = 0
        total_duration = 0
        dropped_nodes = []

        time_dimension = routing.GetDimensionOrDie('Time')

        for vehicle_id in range(self.num_vehicles):
            route = {
                'vehicle_id': vehicle_id,
                'stops': [],
                'distance_km': 0.0,
                'duration_minutes': 0.0
            }

            index = routing.Start(vehicle_id)
            route_distance = 0
            route_duration = 0

            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                time_var = time_dimension.CumulVar(index)

                route['stops'].append({
                    'location_index': node_index,
                    'time_minutes': solution.Min(time_var)
                })

                # Get next index
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                next_node = manager.IndexToNode(index)

                # Add distance and time to next stop
                route_distance += self.distance_matrix[node_index][next_node]
                route_duration += self.duration_matrix[node_index][next_node]

            # Add final node (return to depot)
            node_index = manager.IndexToNode(index)
            time_var = time_dimension.CumulVar(index)

            route['stops'].append({
                'location_index': node_index,
                'time_minutes': solution.Min(time_var)
            })

            route['distance_km'] = route_distance
            route['duration_minutes'] = route_duration

            # Only add routes that have stops (beyond depot start/end)
            if len(route['stops']) > 2:
                routes.append(route)
                total_distance += route_distance
                total_duration += route_duration

        # Check for dropped nodes
        for node in range(1, self.num_locations):
            index = manager.NodeToIndex(node)
            if solution.Value(routing.NextVar(index)) == index:
                dropped_nodes.append(node)

        return {
            'routes': routes,
            'total_distance_km': total_distance,
            'total_duration_minutes': total_duration,
            'num_routes': len(routes),
            'dropped_nodes': dropped_nodes,
            'objective_value': solution.ObjectiveValue()
        }


def format_time(minutes: int) -> str:
    """Convert minutes from start to HH:MM format."""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def parse_time(time_str: str, base_time: datetime) -> int:
    """
    Convert time string to minutes from base_time.

    Args:
        time_str: Time in "HH:MM" format
        base_time: Base datetime to calculate from

    Returns:
        Minutes from base_time
    """
    if not time_str:
        return 0

    hours, minutes = map(int, time_str.split(':'))
    target_time = base_time.replace(hour=hours, minute=minutes, second=0)
    delta = target_time - base_time

    return int(delta.total_seconds() / 60)
