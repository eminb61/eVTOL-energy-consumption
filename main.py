import argparse
import pandas as pd
from aircraft import Aircraft
from utils.helpers import load_config, update_is_first_last_time
import logging
import os
import pprint

def compute_energy_consumption(route, flight_directions, aircraft):
    energy_consumptions = []
    for flight_direction in flight_directions:
        aircraft.flight_direction = flight_direction
        for _, row in route.iterrows():
            if row['flight_direction'] == flight_direction:
                phase_info = {
                    'horizontal_distance': row['distance_to_next_meters'],
                    'vertical_distance': row['altitude_difference'],
                    'horizontal_velocity': row['horizontal_velocity'],
                    'vertical_velocity': row['vertical_velocity'],
                    'travel_time': row['time_to_complete'],
                    'altitude': row['altitude'],
                    'is_first_last_time': row['is_first_last_time']
                }
                if row['phase'] == 'HOVER CLIMB':
                    energy_consumption = aircraft.hover_climb_phase(phase_info)
                elif row['phase'] == 'CLIMB TRANSITION':
                    energy_consumption = aircraft.climb_transition_phase(phase_info)
                elif row['phase'] == 'CLIMB':
                    energy_consumption = aircraft.climb_phase(phase_info)
                elif row['phase'] == 'CRUISE':
                    energy_consumption = aircraft.cruise_phase(phase_info)      
                elif row['phase'] == 'DESCENT':
                    energy_consumption = aircraft.descent_phase(phase_info)  
                elif row['phase'] == 'DESCENT TRANSITION':
                    energy_consumption = aircraft.descent_transition_phase(phase_info)  
                elif row['phase'] == 'HOVER DESCENT':
                    energy_consumption = aircraft.hover_descent_phase(phase_info)   
                elif row['phase'] == 'END':
                    energy_consumption = None
                    pass
                else:
                    raise ValueError('phase must be one of the following: HOVER CLIMB, CLIMB TRANSITION, CLIMB, CRUISE, DESCENT, DESCENT TRANSITION, HOVER DESCENT')
                
                energy_consumptions.append(energy_consumption)
    route['energy_consumption'] = energy_consumptions
    return route


def setup_logging():
    log_file = os.path.join(os.path.dirname(__file__), '..', 'logs/energy.log')
    logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def parse_arguments():
    parser = argparse.ArgumentParser(description="Compute Energy Consumption for Flight Profile")
    parser.add_argument('-f', '--file', required=True, help="Path to the route file")
    parser.add_argument('-d', '--directions', nargs='+', required=True, help="List of flight directions")
    return parser.parse_args()


if __name__ == "__main__":
    setup_logging()
    args = parse_arguments()

    logging.info(f"Computing energy consumption for flight directions: {args.directions}")

    route = pd.read_csv(args.file)
    route = update_is_first_last_time(route, args.directions)
    aircraft_params = load_config("./aircraft_params.json")
    aircraft = Aircraft(aircraft_params=aircraft_params, flight_directions=args.directions)
    updated_route = compute_energy_consumption(route, args.directions, aircraft)

    pprint.pprint(aircraft.metrics)
    aircraft.print_total_energy_consumption()
    aircraft.print_total_flight_time()

    logging.info(f"Total energy consumption: {aircraft.get_total_energy_consumption()}")
    logging.info(f"Total flight time: {aircraft.get_total_flight_time()}")

    # updated_route.to_csv('data/output_route.csv', index=False)

