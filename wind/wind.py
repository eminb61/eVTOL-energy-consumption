import numpy as np
from math import sin, asin, pi
from utils.vector_math import vector_to_heading, swap_angle_relative_x_axis_north, heading_to_vector, magnitude, convert_to_range_zero_to_two_pi
from utils.units import degrees_to_radians, mph_to_metersec
import logging

class Wind:

    def __init__(self, reference_frame, wind_magnitude_mph=0, wind_direction_degrees=0):
        self.reference_frame = reference_frame
        self.wind_magnitude = mph_to_metersec(wind_magnitude_mph)
        self.wind_angle = degrees_to_radians(wind_direction_degrees)
            
    @staticmethod
    def ground_velocity(true_air_velocity: np.ndarray, v_wind: np.ndarray) -> np.ndarray:
        """Calculate the ground velocity."""
        return np.add(true_air_velocity, v_wind)
    
    @staticmethod
    def wind_adjusted_true_velocity(cruise_speed: float, desired_heading: float, v_wind: np.ndarray, ground_speed_threshold: float = None) -> np.ndarray:
        """Calculate the true velocity required to move the aircraft in the desired heading, in the presence of wind.
        Heading of the aircraft may change. True airspeed not adjusted unless ground speed < threshold. 
        
        Central Equation: sin(a - c) = (|B| / |A|)sin(b - a), 
        where a = desired_heading, c = true_heading, b = wind_heading all relative to the x-axis (using swap_angle_relative_x_axis_north),
        and |B| = wind_mag and |A| = cruise_speed.
        """
        logging.info(f"PROCESSING VELOCITY FOR WIND: Cruise speed = {cruise_speed}, Desired heading = {desired_heading}, Wind vector = {v_wind}")
        wind_mag = magnitude(v_wind)
        a = swap_angle_relative_x_axis_north(desired_heading)
        b = swap_angle_relative_x_axis_north(vector_to_heading(v_wind))
        B_over_A = wind_mag / cruise_speed
        
        if B_over_A > 1: # TODO: better address unsolvable case
            return Wind.rta_velocity_wind_adjusted(ground_speed_threshold, desired_heading, v_wind)
        
        right_hand_side = B_over_A * sin(b - a)
        
        if right_hand_side < -1 - 0.5 or right_hand_side > 1 + 0.5:
            print(a, b, wind_mag, cruise_speed, wind_mag / cruise_speed)
            raise ValueError(f"The RHS={right_hand_side} is outside (-1, 1).")
        
        c = a - asin(min(max(right_hand_side, -1), 1)) # technically, c = a - asin(rhs) - 2pi * k, min and max prevent rounding errors
        required_heading = swap_angle_relative_x_axis_north(c)

        logging.info(f"Desired heading = {desired_heading}, Required heading = {required_heading}")
        
        # new velocities
        true_velocity = heading_to_vector(required_heading, magnitude=cruise_speed)
        ground_velocity = Wind.ground_velocity(true_velocity, v_wind)

        logging.info(f"BEFORE RTA VELOCITY WIND ADJUSTMENT: True velocity = {true_velocity}, Ground velocity = {ground_velocity}")
                
        # if ground_speed @ given true_airspeed < threshold, return the minimum true velocity needed to fly in the desired heading @ threshold
        if ground_speed_threshold and magnitude(ground_velocity) < ground_speed_threshold:
            return Wind.rta_velocity_wind_adjusted(ground_speed_threshold, desired_heading, v_wind)
        
        return true_velocity

    @staticmethod
    def rta_velocity_wind_adjusted(desired_speed: float, desired_heading: float, v_wind: np.ndarray) -> np.ndarray:
        """Calculate the true velocity requried to move the aircraft in the desired heading at the desired speed, in the presence of wind. 
        True airspeed and initial heading of the aircraft may change.       
        
        Returns:
         np.array: Velocity vector required to move with the desired heading at the desired speed.
        """
        
        v_desired = heading_to_vector(desired_heading, magnitude=desired_speed)

        logging.info(f"AFTER RTA VELOCITY WIND ADJUSTMENT: {np.subtract(v_desired, v_wind)}")
        
        return np.subtract(v_desired, v_wind)
    
    @staticmethod
    def make_static_wind_vector_relative_to_the_aircraft(wind_angle: float, aircraft_heading: float, wind_magnitude: float = None) -> np.ndarray:
        """Generate a wind vector with a desired angle (radians) relative to the aircraft's heading 
         (0 = tailwind, 0.5pi = starboard crosswind, pi = headwind, 1.5pi = port crosswind).
        """
        
        assert(0 <= wind_angle <= 2 * pi), "Angle must be in radians, and between 0 and 2pi."
    
        wind_heading = wind_angle + aircraft_heading
                
        return heading_to_vector(wind_heading, magnitude=wind_magnitude)

    @staticmethod
    def make_wind_vector_relative_to_north(wind_origin_heading: float, wind_magnitude: float = 8.0) -> np.ndarray:
        """Generate a wind vector coming from wind_origin_heading, where wind_origin_heading is relative to north.
        (0 = South wind, 0.5pi = West wind, pi = North wind, 1.5pi = East wind).
        """
        
        # Ensure angles are in the correct range
        assert(0 <= wind_origin_heading <= 2 * np.pi + 0.01), f"Wind angle must be in radians, and between 0 and 2pi. Wind angle = {wind_origin_heading}"
        
        return heading_to_vector(wind_origin_heading + pi, magnitude=wind_magnitude)        
    
    def compute_aircraft_velocity(self, destination_heading, true_airspeed_desired: float, ground_speed_threshold: float) -> (np.ndarray, np.ndarray):
        """ Computes the true velocity vector of the aircraft such that the aircraft flies toward its 
        destination with respect to the ground in the presence of cross wind, while only applying the 
        desired (power optimal) true airspeed.
        
        Returns: (true_velocity_vector: np.ndarray, ground_velocity_vector: np.ndarray)
        
        Airspeed affects power. Ground speed affects travel time, which then affects total energy consumption. 
        Therefore, the effects of wind on power are decoupled from those on travel time, and we can change the 
        heading of the aircraft without changing its airspeed (unless ground speed < threshold) such that the 
        aircraft flies in the right direction relative to the ground in the presence of crosswind."""
        
        # compute wind vector in the context of the aircraft
        if self.reference_frame == 'relative_to_aircraft':
            v_wind: np.ndarray = Wind.make_static_wind_vector_relative_to_the_aircraft(self.wind_angle, destination_heading, self.wind_magnitude)
        elif self.reference_frame == 'relative_to_north':
            v_wind: np.ndarray = Wind.make_wind_vector_relative_to_north(self.wind_angle, self.wind_magnitude)
            logging.info(f"Wind vector relative to North: {v_wind}")
  
        # note: |true_vector| = true_airspeed_desired UNLESS wind is too strong, and a greater true_airspeed is needed
        true_vector = Wind.wind_adjusted_true_velocity(cruise_speed=true_airspeed_desired, 
                                                       desired_heading=destination_heading, 
                                                       v_wind=v_wind, 
                                                       ground_speed_threshold=ground_speed_threshold)
        ground_vector = Wind.ground_velocity(true_vector, v_wind)
        
        # Verify aircraft flight direction and speeds.
        Wind.verify_aircraft_heading(ground_vector, destination_heading)
        Wind.verify_aircraft_speeds(ground_vector, ground_speed_threshold, true_airspeed_desired, true_vector)
        
        return (true_vector, ground_vector)
    
    # --- VERIFICATION -- 
    @staticmethod
    def verify_aircraft_heading(ground_v: np.ndarray, destination_heading: float) -> None:
        aircraft_heading = convert_to_range_zero_to_two_pi(vector_to_heading(ground_v))
        destination_heading = convert_to_range_zero_to_two_pi(destination_heading)
        assert abs(aircraft_heading - destination_heading) < 1e-9, f'Wrong direction. Aircraft heading = {aircraft_heading}, Destination Heading = {destination_heading}.'
    
    @staticmethod
    def verify_aircraft_speeds(ground_v: np.ndarray, ground_threshold: float, desired_true_airspeed: float, adjusted_true_v: np.ndarray) -> None: 
        ground_speed = magnitude(ground_v)
        assert ground_speed > ground_threshold or abs(ground_speed - ground_threshold) < 1e-9, f'Aircraft is not flying fast enough. Ground speed = {ground_speed}. Minimum = {ground_threshold}.'
        if not (abs(ground_speed - ground_threshold) < 1e-9): # the aircraft was able to maintain its heading flying @ true_airspeed
            true_airspeed = magnitude(adjusted_true_v)
            assert abs(true_airspeed - desired_true_airspeed) < 1e-9, f'Aircraft true airspeed is not equal to desired true airspeed. Desired true airspeed = {desired_true_airspeed}, Actual true airspeed = {true_airspeed}.'