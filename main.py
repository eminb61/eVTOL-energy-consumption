import argparse
import pandas as pd
from aircraft import Aircraft
from utils.helpers import load_config, update_is_first_last_time, save_to_database
from wind.wind import Wind
import logging
import datetime
import os
import pprint

def compute_energy_consumption(route, flight_directions, aircraft):
    energy_consumptions = []
    time_to_complete_list = []
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
                    'is_first_last_time': row['is_first_last_time'],
                    'latitude': row['latitude'],
                    'longitude': row['longitude']
                }
                if row['phase'] == 'HOVER CLIMB':
                    energy_consumption, time_to_complete = aircraft.hover_climb_phase(phase_info)
                elif row['phase'] == 'CLIMB TRANSITION':
                    energy_consumption, time_to_complete = aircraft.climb_transition_phase(phase_info)
                elif row['phase'] == 'CLIMB':
                    energy_consumption, time_to_complete = aircraft.climb_phase(phase_info)
                elif row['phase'] == 'CRUISE':
                    energy_consumption, time_to_complete = aircraft.cruise_phase(phase_info)      
                elif row['phase'] == 'DESCENT':
                    energy_consumption, time_to_complete = aircraft.descent_phase(phase_info)  
                elif row['phase'] == 'DESCENT TRANSITION':
                    energy_consumption, time_to_complete = aircraft.descent_transition_phase(phase_info)  
                elif row['phase'] == 'HOVER DESCENT':
                    energy_consumption, time_to_complete = aircraft.hover_descent_phase(phase_info)   
                elif row['phase'] == 'END':
                    energy_consumption = time_to_complete = None
                    pass
                else:
                    raise ValueError('phase must be one of the following: HOVER CLIMB, CLIMB TRANSITION, CLIMB, CRUISE, DESCENT, DESCENT TRANSITION, HOVER DESCENT')
                
                energy_consumptions.append(energy_consumption)
                time_to_complete_list.append(time_to_complete)
    route['energy_consumption'] = energy_consumptions
    route['time_to_complete'] = time_to_complete_list
    return route


def setup_logging():
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_file = os.path.join(os.path.dirname(__file__), '..', f'logs/energy-{timestamp}.log')
    logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def parse_arguments():
    parser = argparse.ArgumentParser(description="Compute Energy Consumption for Flight Profile")
    parser.add_argument('-f', '--file', required=True, help="Path to the route file")
    parser.add_argument('-ws', '--wind_speed', type=int, required=True, help="Wind speed (int)")
    parser.add_argument('-wd', '--wind_direction', type=int, required=True, help="Wind direction (int)")
    return parser.parse_args()


if __name__ == "__main__":
    # setup_logging()
    args = parse_arguments()

    route = pd.read_csv(args.file)
    flight_directions = route['flight_direction'].unique()
    logging.info(f"Computing energy consumption for flight directions: {flight_directions}")

    route = update_is_first_last_time(route, flight_directions)

    reference_frame = 'relative_to_aircraft'
    wind_magnitude_mph = args.wind_speed
    wind_direction_degrees = args.wind_direction

    wind = Wind(reference_frame=reference_frame,
                wind_direction_degrees=wind_direction_degrees, 
                wind_magnitude_mph=wind_magnitude_mph)

    aircraft_params = load_config("./aircraft_params.json")
    aircraft = Aircraft(aircraft_params=aircraft_params, flight_directions=flight_directions, wind=wind)
    updated_route = compute_energy_consumption(route, flight_directions, aircraft)

    pprint.pprint(aircraft.metrics)
    aircraft.print_total_energy_consumption()
    aircraft.print_total_flight_time()

    total_energy_consumption = aircraft.get_total_energy_consumption()
    total_flight_time = aircraft.get_total_flight_time()
    print(total_energy_consumption)
    print(total_flight_time)
    logging.info(f"Total energy consumption: {total_energy_consumption}")
    logging.info(f"Total flight time: {total_flight_time}")

    save_to_database(total_energy_consumption, 
                     total_flight_time, 
                     wind_direction_degrees, 
                     wind_magnitude_mph)


    updated_route.to_csv('../data/output_route.csv', index=False)

