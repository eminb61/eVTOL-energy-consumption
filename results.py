import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns


def get_df(file_path, metric):
    conn = sqlite3.connect(file_path)
    query = f"SELECT id, {metric} FROM op_summary_statistics"
    df = pd.read_sql_query(query, conn)
    conn.close()
    df[['distance', 'angle', 'speed']] = df['id'].str.split('_', expand=True)
    df[['distance', 'angle', 'speed']] = df[['distance', 'angle', 'speed']].astype(int)
    return df


def surface_plot(metric_name, metric_label, distances, file_path):
    df = get_df(file_path, metric_name)

    # Plotting 3D Surface Plot
    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(111, projection='3d')

    # Colors for different distances
    colors = ['red', 'blue', 'green', 'purple', 'orange']
    color_idx = 0

    for dist in distances:
        # Filter for each distance
        df_dist = df[df['distance'] == dist]

        # Plotting
        scatter = ax.scatter(df_dist['angle'], df_dist['speed'], df_dist[metric_name], 
                             c=colors[color_idx], marker='o', s=50, label=f'{dist} miles')
        color_idx += 1

    # Labels and title
    ax.set_ylabel('Wind Speed (mph)')
    ax.set_zlabel(f'{metric_label}')
    ax.set_title(f'{metric_label} for Various Distances in a Vertiport Network')
    ax.set_xticks([0, 90, 180])
    ax.set_yticks(list(range(0, 45, 10)))
    ax.set_xticklabels(['Tailwind', 'Crosswind', 'Headwind'])

    # Legend
    ax.legend()

    # Show plot
    plt.show()


def line_plot_metric_vs_speed(metric_name, metric_label, file_path, wind_direction):
    df = get_df(file_path, metric_name)
    df_filtered = df[(df['angle'] == wind_direction) & (df['speed'] > 0)]
    
    # Setting up colors for different distances
    colors = ['red', 'blue', 'green', 'purple', 'orange']
    plt.figure(figsize=(10, 6))
    dir_name = {0:'Tailwind', 90:'Crosswind', 180:'Headwind'}

    # Loop through each distance and plot
    for idx, dist in enumerate(range(20, 65, 10)):
        df_dist = df_filtered[df_filtered['distance'] == dist].sort_values(by='speed')
        plt.plot(df_dist['speed'], df_dist[metric_name], color=colors[idx], marker='o', label=f'{dist} miles')

    # Adding labels, title, and legend
    plt.xlabel('Wind Speed (mph)')
    plt.xticks(list(range(10, 45, 10)))
    plt.ylabel(metric_label)
    ax = plt.gca() 
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    plt.title(f'{metric_label} vs. Wind Speed for {dir_name[wind_direction]} at Different Vertiport Distances')
    plt.legend(loc='lower left')

    # Show plot
    plt.show()


def line_plot_vs_distance(metric_name, metric_label, file_path):
    df = get_df(file_path, metric_name)
    
    # Filter data for wind speed = 0 and wind angle = 0
    df_filtered = df[(df['speed'] == 0) & (df['angle'] == 0)]

    # Sort the DataFrame by distance
    df_sorted = df_filtered.sort_values(by='distance')

    # Plotting
    plt.figure(figsize=(10, 6))
    plt.plot(df_sorted['distance'], df_sorted[metric_name], marker='o')

    # Setting labels and title
    plt.xlabel('Distance (miles)')
    plt.ylabel(metric_label)
    plt.title(f'{metric_label} vs. Distance for Still Air Conditions')

    # Setting y-axis to have integer ticks
    ax = plt.gca()
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    # Show plot
    plt.show()


def heatmap_wind_direction_speed(metric_name, metric_label, file_path, distance):
    df = get_df(file_path, metric_name)
    df = df[df['distance'] == distance]

    # Find the metric value at wind speed 0 and direction 0
    value_at_zero_speed = df.loc[(df['speed'] == 0) & (df['angle'] == 0), metric_name].iloc[0]

    # Check for missing data points and add them if necessary
    for angle in [90, 180]:
        if not ((df['speed'] == 0) & (df['angle'] == angle)).any():
            new_row = pd.DataFrame({'angle': [angle], 'speed': [0], metric_name: [value_at_zero_speed]})
            df = pd.concat([df, new_row], ignore_index=True)

    # Creating a pivot table for the heatmap
    pivot_table = df.pivot_table(index='angle', columns='speed', values=metric_name, aggfunc='mean')

    # Plotting the heatmap
    plt.figure(figsize=(12, 7))
    sns.heatmap(pivot_table, annot=True, cmap='coolwarm', fmt=".2f")

    # Adding labels and title
    plt.title(f"Heatmap of {metric_label} by Wind Direction and Speed for {distance} mile Vertiport Network")
    plt.ylabel('Wind Direction (degrees)')
    plt.xlabel('Wind Speed (mph)')

    # Show the plot
    plt.show()


def heatmap_speed_distance(metric_name, metric_label, file_path, wind_direction):
    df = get_df(file_path, metric_name)

    # Filter the DataFrame for the specified wind direction
    df = df[df['angle'] == wind_direction]

    # Creating a pivot table for the heatmap
    # 'distance' as rows (y-axis), 'speed' as columns (x-axis)
    pivot_table = df.pivot_table(index='distance', columns='speed', values=metric_name, aggfunc='mean')

    # Plotting the heatmap
    plt.figure(figsize=(12, 7))
    sns.heatmap(pivot_table, annot=True, cmap='coolwarm', fmt=".2f")

    # Adding labels and title
    directions = {0: 'Tailwind', 90: 'Crosswind', 180: 'Headwind'}
    plt.title(f"Heatmap of {metric_label} by Vertiport Distance and Wind Speed in a {directions[wind_direction]}")
    plt.ylabel('Vertiport Distance (miles)')
    plt.xlabel('Wind Speed (mph)')

    # Show the plot
    plt.show()


heatmap_speed_distance('fleet_size', 'Optimal Fleet Size', 'energy_and_flight_time/wind_variation_result_Jan18.sqlite', 180)
heatmap_wind_direction_speed('fleet_size', 'Optimal Fleet Size', 'energy_and_flight_time/wind_variation_result_Jan18.sqlite', 60)
line_plot_vs_distance('fleet_size', 'Optimal Fleet Size', 'energy_and_flight_time/wind_variation_result_Jan18.sqlite')
line_plot_metric_vs_speed('fleet_size', 'Optimal Fleet Size', 'energy_and_flight_time/wind_variation_result_Jan18.sqlite', 0)
surface_plot('fleet_size', 'Optimal Fleet Size', [20, 60], 'energy_and_flight_time/wind_variation_result_Jan18.sqlite')
