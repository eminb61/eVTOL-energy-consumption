# Run main.py multiple times with different wind configs
import subprocess

wind_speeds = [10, 20, 30, 40] # mph
wind_directions = [0, 90, 180] # degrees
file_path = 'routes/sfo_sjc_route_60_miles.csv'

for ws in wind_speeds:
    for wd in wind_directions:
        command = f'python3 main.py --file {file_path} --wind_speed {ws} --wind_direction {wd}'
        subprocess.run(command, shell=True)
        print(f'Completed run with wind speed {ws}mph and wind direction {wd} degrees relative to the aircraft.')
