from utils.units import sec_to_hr, sec_to_ms, watt_to_kw
import numpy as np
from power_model import vertical_takeoff_landing_phase_power, climb_transition_phase_power, climb_phase_power, descent_phase_power, \
    cruise_phase_power, descent_transition_phase_power
from flight_helpers import stall_speed
from utils.vector_math import lat_long_to_heading, magnitude
from utils.helpers import log_phase_info, log_location_and_speed, log_wind_speed, log_wind_travel_time
import logging

class Aircraft:
    def __init__(self, aircraft_params, flight_directions, wind):
        self.aircraft_params = aircraft_params
        self.flight_directions = flight_directions
        self.wind = wind
        self.flight_direction = None
        self.prev_vertical_velocity = 0
        self.prev_horizontal_velocity = 0
        self.prev_latitude = None
        self.prev_longitude = None
        self.latitude = None
        self.longitude = None
        self.altitude = 0
        self.mtom = self.aircraft_params['mtom'] # Max takeoff mass
        self.wing_area = self.aircraft_params['wing_area'] # Wing area (m^2)
        self.disk_load = self.aircraft_params['disk_load'] # Disk loading (kg/m^2)    
        self.f = self.aircraft_params['f'] # Correction factor for interference from the fuselage            
        self.FoM = self.aircraft_params['FoM'] # Figure of merit
        self.cd_0 = self.aircraft_params['cd_0'] # Zero lift drag coefficient
        self.cl_max = self.aircraft_params['cl_max'] # Max lift coefficient
        self.ld_max = self.aircraft_params['ld_max'] # Max lift to drag ratio
        self.eta_hover = self.aircraft_params['eta_hover'] # Hover efficiency
        self.eta_descend = self.aircraft_params['eta_descend'] # Descend efficiency
        self.eta_climb = self.aircraft_params['eta_climb'] # Climb efficiency
        self.eta_cruise = self.aircraft_params['eta_cruise'] # Cruise efficiency
        self.atmosphere_condition = self.aircraft_params['atmosphere_condition']   
        self.stall_speed = self.compute_stall_speed()
        self.metrics = Aircraft._initialize_metrics(flight_directions)

    @staticmethod
    def _initialize_metrics(flight_directions):
        metrics = {}
        initial_phase_dict = {
            'hover_climb': 0,
            'climb_transition': 0,
            'climb': 0,
            'cruise': 0,
            'descent': 0,
            'descent_transition': 0,
            'hover_descent': 0
        }

        for direction in flight_directions:
            metrics[direction] = {
                'phase_energy': initial_phase_dict.copy(),
                'phase_time': initial_phase_dict.copy()
            }

        return metrics        

    def extract_phase_info(self, phase_info):
        self.horizontal_distance = phase_info['horizontal_distance']
        self.vertical_distance = phase_info['vertical_distance']
        self.horizontal_velocity = phase_info['horizontal_velocity']
        self.vertical_velocity = phase_info['vertical_velocity']
        self.travel_time = phase_info['travel_time']
        self.altitude = phase_info['altitude']
        self.is_first_last_time = phase_info['is_first_last_time']
        self.latitude = phase_info['latitude']
        self.longitude = phase_info['longitude']
    
    def compute_air_speed(self, horizontal_velocity, vertical_velocity):
        return np.sqrt(horizontal_velocity**2 + vertical_velocity**2)
    
    def compute_destination_heading(self):
        """Compute aircraft heading (from current location toward destination waypoint). """
        return lat_long_to_heading(self.prev_latitude, self.prev_longitude, self.latitude, self.longitude)
                
    def hover_climb_phase(self, phase_info):
        """Hover climb phase of the takeoff."""
        self.extract_phase_info(phase_info)
        log_phase_info(aircraft=self, phase='HOVER CLIMB')
        log_location_and_speed(aircraft=self)

        self.metrics[self.flight_direction]['phase_time']['hover_climb'] += round(self.travel_time, 2)
        energy_consumption = round(
            self.vertical_takeoff_landing_energy_consumption(start_altitude=self.altitude,
                                                             end_altitude=self.altitude+self.vertical_distance,
                                                             hover_time=self.travel_time,
                                                             operation='takeoff'), 2)
        self.metrics[self.flight_direction]['phase_energy']['hover_climb'] += energy_consumption
        self.update_location_and_velocity(horizontal_velocity=self.horizontal_velocity, vertical_velocity=self.vertical_velocity)
        log_location_and_speed(aircraft=self)

        return energy_consumption, round(self.travel_time, 2)

    def climb_transition_phase(self, phase_info):
        """Climb transition phase of the takeoff."""
        self.extract_phase_info(phase_info)
        log_phase_info(aircraft=self, phase='CLIMB TRANSITION')
        log_location_and_speed(aircraft=self)
        self.metrics[self.flight_direction]['phase_time']['climb_transition'] += round(self.travel_time, 2)

        # TODO: !!! Use wind adjusted speeds
        start_air_speed, end_air_speed, true_v, ground_v = self.adjust_speed_based_on_wind()
        log_wind_speed(start_air_speed, end_air_speed, true_v, ground_v)

        energy_consumption = round(
            self.climb_transition_energy_consumption(climb_transition_end_altitude=self.altitude+self.vertical_distance,
                                                     climb_transition_time=self.travel_time,
                                                     start_air_speed=start_air_speed,
                                                     end_air_speed=end_air_speed), 2)
        self.metrics[self.flight_direction]['phase_energy']['climb_transition'] += energy_consumption
        # Update previous velocity and location
        horizontal_velocity = self.compute_horizontal_speed_component(true_v[1], self.vertical_velocity)
        self.update_location_and_velocity(horizontal_velocity=magnitude(true_v), vertical_velocity=self.vertical_velocity)
        log_location_and_speed(aircraft=self)
        return energy_consumption

    def climb_phase(self, phase_info):
        """Climbing to cruise altitude phase."""
        self.extract_phase_info(phase_info)
        log_phase_info(aircraft=self, phase='CLIMB')
        log_location_and_speed(aircraft=self)
        self.metrics[self.flight_direction]['phase_time']['climb'] += round(self.travel_time, 2)

        start_air_speed, end_air_speed, true_v, ground_v = self.adjust_speed_based_on_wind()
        log_wind_speed(start_air_speed, end_air_speed, true_v, ground_v)

        energy_consumption = round(
            self.climb_energy_consumption(climb_end_altitude=self.altitude+self.vertical_distance,
                                          climb_time=self.travel_time,
                                          start_air_speed=start_air_speed,
                                          end_air_speed=end_air_speed), 2)
        self.metrics[self.flight_direction]['phase_energy']['climb'] += energy_consumption
        # Update previous velocity and location
        horizontal_velocity = self.compute_horizontal_speed_component(true_v[1], self.vertical_velocity)
        self.update_location_and_velocity(horizontal_velocity=magnitude(true_v), vertical_velocity=self.vertical_velocity)
        log_location_and_speed(aircraft=self)
        return energy_consumption
    
    def cruise_phase(self, phase_info):
        """Cruise phase of the mission."""
        self.extract_phase_info(phase_info)
        log_phase_info(aircraft=self, phase='CRUISE')
        log_location_and_speed(aircraft=self)
        
        start_air_speed, end_air_speed, true_v, ground_v = self.adjust_speed_based_on_wind()
        log_wind_speed(start_air_speed, end_air_speed, true_v, ground_v)

        link_traversal_time = self.compute_travel_time_from_speed(distance=self.horizontal_distance,
                                                                  horizontal_speed=magnitude(ground_v)) 

        self.travel_time = link_traversal_time
        log_wind_travel_time(link_traversal_time)
        self.metrics[self.flight_direction]['phase_time']['cruise'] += round(self.travel_time, 2)       

        energy_consumption = round(
            self.cruise_energy_consumption(time_cruise=self.travel_time, cruise_speed=magnitude(true_v)), 2)
        self.metrics[self.flight_direction]['phase_energy']['cruise'] += energy_consumption
        horizontal_velocity = self.compute_horizontal_speed_component(true_v[1], self.vertical_velocity)
        self.update_location_and_velocity(horizontal_velocity=magnitude(true_v), vertical_velocity=self.vertical_velocity)
        log_location_and_speed(aircraft=self)
        return energy_consumption, link_traversal_time
        
    def descent_phase(self, phase_info):
        """Descending from cruise altitude phase."""
        self.extract_phase_info(phase_info)
        log_phase_info(aircraft=self, phase='DESCENT')
        log_location_and_speed(aircraft=self)
        self.metrics[self.flight_direction]['phase_time']['descent'] += round(self.travel_time, 2)

        start_air_speed, end_air_speed, true_v, ground_v = self.adjust_speed_based_on_wind()
        log_wind_speed(start_air_speed, end_air_speed, true_v, ground_v)

        energy_consumption = round(
            self.descent_energy_consumption(descend_end_altitude=self.altitude-self.vertical_distance,
                                            descend_time=self.travel_time,
                                            start_air_speed=start_air_speed,
                                            end_air_speed=end_air_speed), 2)
        
        self.metrics[self.flight_direction]['phase_energy']['descent'] += energy_consumption

        horizontal_velocity = self.compute_horizontal_speed_component(true_v[1], self.vertical_velocity)
        self.update_location_and_velocity(horizontal_velocity=magnitude(true_v), vertical_velocity=self.vertical_velocity)
        log_location_and_speed(aircraft=self)
        return energy_consumption
    
    def descent_transition_phase(self, phase_info):
        """Descent transition phase of the landing."""
        self.extract_phase_info(phase_info)
        log_phase_info(aircraft=self, phase='DESCENT TRANSITION')
        log_location_and_speed(aircraft=self)
        self.metrics[self.flight_direction]['phase_time']['descent_transition'] += round(self.travel_time, 2)

        start_air_speed, end_air_speed, true_v, ground_v = self.adjust_speed_based_on_wind()
        log_wind_speed(start_air_speed, end_air_speed, true_v, ground_v)

        energy_consumption = round(
            self.descent_transition_energy_consumption(descend_transition_end_altitude=self.altitude-self.vertical_distance,
                                                       descend_transition_time=self.travel_time,
                                                       start_air_speed=start_air_speed,
                                                       end_air_speed=end_air_speed), 2)
        
        self.metrics[self.flight_direction]['phase_energy']['descent_transition'] += energy_consumption
        horizontal_velocity = self.compute_horizontal_speed_component(true_v[1], self.vertical_velocity)
        self.update_location_and_velocity(horizontal_velocity=magnitude(true_v), vertical_velocity=self.vertical_velocity)
        log_location_and_speed(aircraft=self)
        return energy_consumption

    def hover_descent_phase(self, phase_info):
        """Hover descent phase of the landing."""
        self.extract_phase_info(phase_info)
        log_phase_info(aircraft=self, phase='HOVER DESCENT')
        log_location_and_speed(aircraft=self)
        self.metrics[self.flight_direction]['phase_time']['hover_descent'] += round(self.travel_time, 2)
        energy_consumption = round(
            self.vertical_takeoff_landing_energy_consumption(start_altitude=self.altitude,
                                                             end_altitude=self.altitude-self.vertical_distance,
                                                             hover_time=self.travel_time,
                                                             operation='landing'), 2)
        self.metrics[self.flight_direction]['phase_energy']['hover_descent'] += energy_consumption
        self.update_location_and_velocity(horizontal_velocity=self.horizontal_velocity, vertical_velocity=self.vertical_velocity)
        log_location_and_speed(aircraft=self)        
        return energy_consumption, round(self.travel_time, 2)

    def vertical_takeoff_landing_energy_consumption(self, start_altitude: float, end_altitude, hover_time: float, operation: str) -> float:
        
        self.tom = self.mtom - (self.aircraft_params['pax'])*self.aircraft_params['pax_mass']
        
        vertical_takeoff_landing_power = vertical_takeoff_landing_phase_power(start_altitude=start_altitude,
                                                                              end_altitude=end_altitude,
                                                                              aircraft_params=self.aircraft_params,
                                                                              tom=self.tom,
                                                                              vertical_velocity=self.vertical_velocity)
        vertical_takeoff_landing_power = watt_to_kw(vertical_takeoff_landing_power)

        if operation == 'takeoff':
            return sec_to_hr(vertical_takeoff_landing_power * hover_time) # kWh - time units need to be seconds
        elif operation == 'landing':
            return sec_to_hr(vertical_takeoff_landing_power * hover_time)
        else:
            raise ValueError('operation must be either takeoff or landing')

    def climb_transition_energy_consumption(self, 
                                            climb_transition_end_altitude: float,
                                            climb_transition_time: float,
                                            start_air_speed,
                                            end_air_speed) -> float:
        climb_transition_power = climb_transition_phase_power(start_altitude=self.altitude, 
                                                              end_altitude=climb_transition_end_altitude, 
                                                              aircraft_params=self.aircraft_params, 
                                                              tom=self.tom, 
                                                              start_vertical_velocity=self.prev_vertical_velocity,
                                                              end_vertical_velocity=self.vertical_velocity,
                                                              start_air_speed=start_air_speed,
                                                              end_air_speed=end_air_speed,
                                                              is_first_time=self.is_first_last_time)
        # Convert from watts to kilowatts
        climb_transition_power = watt_to_kw(climb_transition_power)

        # Energy = Power * Time
        return sec_to_hr(climb_transition_power * climb_transition_time)
    
    def climb_energy_consumption(self, 
                                 climb_end_altitude: float, 
                                 climb_time: float,
                                 start_air_speed: float,
                                 end_air_speed: float) -> float:
        climb_power = climb_phase_power(start_altitude=self.altitude, 
                                        end_altitude=climb_end_altitude, 
                                        aircraft_params=self.aircraft_params, 
                                        tom=self.tom, 
                                        start_vertical_velocity=self.prev_vertical_velocity, 
                                        end_vertical_velocity=self.vertical_velocity,
                                        start_air_speed=start_air_speed,
                                        end_air_speed=end_air_speed,
                                        )
        climb_power = watt_to_kw(climb_power)

        return sec_to_hr(climb_power * climb_time)    
    
    def descent_energy_consumption(self, 
                                   descend_end_altitude: float, 
                                   descend_time: float,
                                   start_air_speed: float,
                                   end_air_speed: float) -> float:
        """
        Computes the energy consumption during the descent phase of the mission.
        :param min_power_velocity: The minimum power speed of the aircraft in meters per second.
        :param descend_end_altitude: The altitude at which the descent ends in meters.
        :param descend_time: The time spent in the descent phase in seconds.
        :return: The energy consumption during the descent phase of the mission in kWh.
        """
        descend_power = descent_phase_power(start_altitude=self.altitude,
                                            end_altitude=descend_end_altitude,
                                            aircraft_params=self.aircraft_params,
                                            tom=self.tom,
                                            start_vertical_velocity=self.prev_vertical_velocity,
                                            end_vertical_velocity=self.vertical_velocity,
                                            start_air_speed=start_air_speed,
                                            end_air_speed=end_air_speed
                                            )

        descend_power = watt_to_kw(descend_power)

        return sec_to_hr(descend_power * descend_time)
    
    def descent_transition_energy_consumption(self,
                                              descend_transition_end_altitude: float, 
                                              descend_transition_time: float,
                                              start_air_speed: float,
                                              end_air_speed: float) -> float:
        """
        Computes the energy consumption during the descend transition phase.
        :param velocity: Velocity (m/s)
        :param descend_transition_end_altitude: Altitude at the end of the descend transition phase (meters)
        :param descend_transition_time: Time spent in the descend transition phase (seconds)
        :return: Energy consumption during the descend transition phase (kWh)
        """
        descend_transition_power = descent_transition_phase_power(start_altitude=self.altitude,
                                                                  end_altitude=descend_transition_end_altitude,
                                                                  aircraft_params=self.aircraft_params,
                                                                  tom=self.tom,
                                                                  start_vertical_velocity=self.prev_vertical_velocity,
                                                                  end_vertical_velocity=self.vertical_velocity,
                                                                  start_air_speed=start_air_speed,
                                                                  end_air_speed=end_air_speed,
                                                                  is_last_time=self.is_first_last_time)
        descend_transition_power = watt_to_kw(descend_transition_power)

        return sec_to_hr(descend_transition_power * descend_transition_time)    
    
    def cruise_energy_consumption(self, time_cruise, cruise_speed) -> float:
        # cruise_velocity = min(self.input_cruise_speed, velocity)
        cruise_power = cruise_phase_power(cruise_speed=cruise_speed,
                                          aircraft_params=self.aircraft_params,
                                          tom=self.tom)
        cruise_power = watt_to_kw(cruise_power)
            
        return sec_to_hr(cruise_power * time_cruise)
    
    def compute_stall_speed(self):
            return stall_speed(atmosphere_condition=self.atmosphere_condition,
                               altitude=self.altitude,
                               mtom=self.mtom,
                               wing_area=self.wing_area,
                               cl_max=self.cl_max)  

    def compute_travel_time_from_speed(self, distance: float, horizontal_speed: float) -> float:
        """
        Computes the travel time between two locations given the horizontal speed in m/s. Returns the travel time in secs.
        """
        return round(distance / horizontal_speed)
    
    def adjust_speed_based_on_wind(self, phase: str=None):   
        # Compute start air speed according to the previous speed
        start_air_speed = self.compute_air_speed(self.prev_horizontal_velocity, self.prev_vertical_velocity)
        # Compute end air speed according to the route file
        end_air_speed = self.compute_air_speed(self.horizontal_velocity, self.vertical_velocity)
        logging.info(f"Before Wind Processing: Start air speed = {start_air_speed}, End air speed = {end_air_speed}")

        # average_air_speed = round((start_air_speed + end_air_speed) / 2, 2)

        # Update destination heading
        destination_heading = self.compute_destination_heading()
        
        true_v, ground_v = self.wind.compute_aircraft_velocity(destination_heading=destination_heading,
                                                               true_airspeed_desired=self.horizontal_velocity,
                                                               ground_speed_threshold=0.1)
        
        # Update the end air speed
        end_air_speed = self.compute_air_speed(self.vertical_velocity, magnitude(true_v))  

        
        return start_air_speed, end_air_speed, true_v, ground_v   
    
    def compute_horizontal_speed_component(self, true_horizontal_velocity, vertical_velocity):
        return np.sqrt(abs(true_horizontal_velocity**2 - vertical_velocity**2))
    
    def update_prev_velocity(self, horizontal_velocity, vertical_velocity):
        self.prev_vertical_velocity = vertical_velocity
        self.prev_horizontal_velocity = horizontal_velocity

    def update_prev_location(self, latitude, longitude):
        self.prev_latitude = latitude
        self.prev_longitude = longitude

    def update_location_and_velocity(self, horizontal_velocity, vertical_velocity):
        self.update_prev_velocity(horizontal_velocity, vertical_velocity)
        self.update_prev_location(self.latitude, self.longitude)        

    def get_total_energy_consumption(self):
        total_energy = {}
        for flight_direction, data in self.metrics.items():
            total_energy.update({flight_direction: 0})
            for _, energy in data['phase_energy'].items():
                total_energy[flight_direction] += energy
        return total_energy
    
    def get_total_flight_time(self):
        total_time = {}
        for flight_direction, data in self.metrics.items():
            total_time.update({flight_direction: 0})
            for _, time in data['phase_time'].items():
                total_time[flight_direction] += time
        return total_time
    
    def print_total_energy_consumption(self):
        total_energy = self.get_total_energy_consumption()
        for flight_direction, energy in total_energy.items():
            print(f"Total Energy Consumption for {flight_direction}: {round(energy, 2)} kWh")

    def print_total_flight_time(self):
        total_time = self.get_total_flight_time()
        for flight_direction, time in total_time.items():
            print(f"Total Flight Time for {flight_direction}: {round(time/60, 2)} minutes")