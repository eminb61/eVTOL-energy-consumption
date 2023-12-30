import numpy as np
import pandas as pd
import logging
from utils.units import sec_to_min

def haversine_dist(lat1: float, lon1: float, lat2: float, lon2: float, unit: str = 'mile') -> float:
    # 6367 for distance in KM for miles use 3958
    if unit == 'km':
        r = 6367
    elif unit == 'mile':
        r = 3958
    elif unit == 'meter':
        r = 6367000
    else:
        raise ValueError('Unit must be either km, mile or meters.')

    lat1_rad, lon1_rad = np.radians(lat1), np.radians(lon1)
    lat2_rad, lon2_rad = np.radians(lat2), np.radians(lon2)

    d_lat = lat2_rad - lat1_rad
    d_lon = lon2_rad - lon1_rad
    a = np.sin(d_lat / 2) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(d_lon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    return round(r * c, 2)


# Compute 3D distance between two points
def distance_3d(lat1: float, lon1: float, alt1: float, lat2: float, lon2: float, alt2: float, unit: str = 'meter') -> float:
    """
    Computes the 3D distance between two points. Unit for altitude needs to be consistent with unit for haversine distance.
    """
    dist_2d = haversine_dist(lat1, lon1, lat2, lon2, unit)
    return np.sqrt(dist_2d ** 2 + (alt2 - alt1) ** 2)


# Compute the haversine distance between waypoints for each flight direction. Use haversine_dist function above
def add_distance_column(df):
    # Initialize a list for distances
    distances = []

    # Iterate over the dataframe and calculate distances
    for i in range(len(df)):
        # Check if the next row exists and is in the same flight direction
        if i < len(df) - 1 and df.iloc[i]['flight_direction'] == df.iloc[i + 1]['flight_direction']:
            lat1, lon1 = df.iloc[i]['latitude'], df.iloc[i]['longitude']
            lat2, lon2 = df.iloc[i + 1]['latitude'], df.iloc[i + 1]['longitude']
            distance = haversine_dist(lat1, lon1, lat2, lon2, unit='meter')
            distances.append(distance)
        else:
            # If the next row is a different flight direction or does not exist, set the distance to 0
            distances.append(0)

    # Add the distances list as a new column to the dataframe
    df['distance_to_next_meters'] = distances
    return df

import json
from typing import Any, Dict

def load_config(file_path: str) -> Dict[str, Any]:
    with open(file_path, "r") as file:
        return json.load(file)


def update_is_first_last_time(route, flight_directions):
    # Initialize all values to False
    route['is_first_last_time'] = False

    for direction in flight_directions:
        # Filter the DataFrame for the current flight direction
        direction_df = route[route['flight_direction'] == direction]

        # Find the first 'CLIMB TRANSITION' phase
        first_climb_transition_idx = direction_df[direction_df['phase'] == 'CLIMB TRANSITION'].first_valid_index()
        if first_climb_transition_idx is not None:
            route.at[first_climb_transition_idx, 'is_first_last_time'] = True

        # Find the last 'DESCENT TRANSITION' phase
        last_descent_transition_idx = direction_df[direction_df['phase'] == 'DESCENT TRANSITION'].last_valid_index()
        if last_descent_transition_idx is not None:
            route.at[last_descent_transition_idx, 'is_first_last_time'] = True

    return route

def log_phase_info(aircraft, phase):
    logging.info(f"\nPhase: {phase}")
    logging.info(f"Horizontal velocity: {aircraft.horizontal_velocity} m/s")
    logging.info(f"Vertical velocity: {aircraft.vertical_velocity} m/s")
    logging.info(f"Travel time: {aircraft.travel_time} s")

def log_location_and_speed(aircraft):
    logging.info(f"Altitude: {aircraft.altitude} m")
    logging.info(f"latitude: {aircraft.latitude}")
    logging.info(f"longitude: {aircraft.longitude}")    
    logging.info(f"Previous horizontal velocity: {aircraft.prev_horizontal_velocity} m/s")
    logging.info(f"Previous vertical velocity: {aircraft.prev_vertical_velocity} m/s")
    logging.info(f"Previous latitude: {aircraft.prev_latitude}")
    logging.info(f"Previous longitude: {aircraft.prev_longitude}")

def log_wind_speed(start_air_speed, end_air_speed, true_v, ground_v):
    logging.info(f"Start air speed: {start_air_speed} m/s")
    logging.info(f"End air speed: {end_air_speed} m/s")
    logging.info(f"True velocity: {true_v} m/s")
    logging.info(f"Ground velocity: {ground_v} m/s")

def log_wind_travel_time(travel_time):
    logging.info(f"New travel time under wind: {travel_time} s")


import sqlite3

def save_to_database(energy_consumption, flight_time, wind_direction, wind_magnitude):
    connection = sqlite3.connect('energy_and_flight_time_60_mile_route.sqlite')
    cursor = connection.cursor()

    # create table if needed
    cursor.execute('''CREATE TABLE IF NOT EXISTS flight_metrics
                     (id INTEGER PRIMARY KEY, flight_direction TEXT, 
                      energy_consumption REAL, flight_time REAL, 
                      wind_direction_degrees INTEGER, wind_magnitude_mph INTEGER)''')

    # insert record
    for flight_direction in energy_consumption.keys():
        energy = energy_consumption.get(flight_direction, 0)
        time = sec_to_min(flight_time.get(flight_direction, 0))

        cursor.execute('''INSERT INTO flight_metrics 
                          (flight_direction, energy_consumption, flight_time, 
                           wind_direction_degrees, wind_magnitude_mph)
                          VALUES (?, ?, ?, ?, ?)''', 
                       (flight_direction, energy, time, wind_direction, wind_magnitude))

    connection.commit()
    connection.close()