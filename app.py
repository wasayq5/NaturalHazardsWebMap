import matplotlib
matplotlib.use('Agg')  # This sets the backend to a non-interactive one (Agg) for non-GUI environments.
from flask import Flask, render_template
import folium
import json
import urllib.request
from urllib.request import Request, urlopen
import matplotlib.pyplot as plt
import io
import base64
import numpy as np


app = Flask(__name__)

#categorzing disasters
fgd = folium.FeatureGroup(name="Other Disasters")
fgv = folium.FeatureGroup(name="Volcanoes")
fgf = folium.FeatureGroup(name="Wildfires")
fgs = folium.FeatureGroup(name="Storms")

def disaster_type(event):
    if event == "Severe Storms":
        return fgs
    elif event == "Wildfires":
        return fgf
    elif event == "Volcanoes":
        return fgv
    else:
        return fgd

def marker_color(dis_type):
    if dis_type == fgv:
        return 'darkred'
    elif dis_type == fgf:
        return 'red'
    elif dis_type == fgs:
        return 'blue'
    else:
        return 'lightgray'

def fetch_earthquake_data():
    quake_url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
    qresponse = urlopen(quake_url)
    quake_data_json = json.loads(qresponse.read())
    return quake_data_json

def fetch_disaster_data():
    disasters_url = Request("https://eonet.gsfc.nasa.gov/api/v3/events",
                            headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
    dresponse = urlopen(disasters_url)
    disaster_data_json = json.loads(dresponse.read())
    return disaster_data_json

def create_map():
    m = folium.Map(location=[0, 0], zoom_start=2)

    quake_data_json = fetch_earthquake_data()
    disaster_data_json = fetch_disaster_data()

    #Adding Earthquakes in this block
    print("parsing Earthquake data...")
    fgq = folium.FeatureGroup(name="Earthquakes")
    for i in quake_data_json['features']:
        quake_lat = i["geometry"]["coordinates"][1]
        quake_lon = i["geometry"]["coordinates"][0]
        place = i["properties"]["place"]
        mag = i["properties"]["mag"]
        url = '<a href="' + i["properties"]["url"] + '" target="_blank">More info here</a>'

        if mag >= 2.0:
            fgq.add_child(folium.Marker(location=[quake_lat, quake_lon],
            popup="Hazard/Area: Earthquake, %s, Magnitude: %f, Coordinates: %f,%f, %s" % (place, mag, quake_lat,quake_lon, url),
            icon=folium.Icon(color='orange')))

    #Adding other natural hazards in this block
    print("Parsing data on other disasters...")

    disasters_url = Request("https://eonet.gsfc.nasa.gov/api/v3/events",
    headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'})
    dresponse = urlopen(disasters_url)
    disaster_data_json = json.loads(dresponse.read())

    for i in disaster_data_json['events'][:500]:
        dis_lat = i["geometry"][0]["coordinates"][1]
        dis_lon = i["geometry"][0]["coordinates"][0]
        dis_name = i["title"]
        dis_url = '<a href="' + i["sources"][0]["url"] + '" target="_blank">More info here</a>'


        dis_type = disaster_type(i["categories"][0]["title"])

        if i["geometry"][0]["magnitudeValue"] == None:
            dis_type.add_child(folium.Marker(location=[dis_lat, dis_lon], popup="Hazard/Area: %s, Coordinates: %f, %f, %s" % (dis_name, dis_lat, dis_lon, dis_url),
            icon = folium.Icon(color=marker_color(dis_type))))
        
        else:
            dis_magV = i["geometry"][0]["magnitudeValue"]
            dis_magU = i["geometry"][0]["magnitudeUnit"]
            dis_type.add_child(folium.Marker(location=[dis_lat, dis_lon], popup="Hazard/Area: %s, Coordinates: %f, %f, Magnitude:%f %s, %s\n" % (dis_name, dis_lat, dis_lon, dis_magV, dis_magU, dis_url),
            icon = folium.Icon(color=marker_color(dis_type))))

    print("parsed data on other disasters") 

    m.add_child(fgq)
    m.add_child(fgd)
    m.add_child(fgs)
    m.add_child(fgv)
    m.add_child(fgf)

    m.add_child(folium.LayerControl())
    return m

def plot_earthquake_magnitude_histogram(quake_data_json):
    magnitudes = [i["properties"]["mag"] for i in quake_data_json['features'] if i["properties"]["mag"] >= 0]

    print(f"Earthquake Magnitudes: {magnitudes}")
    # Create custom bin edges to include decimal magnitudes
    bins = np.arange(0, max(magnitudes) + 0.1, 0.1)

    plt.hist(magnitudes, bins=bins, color='orange')
    plt.xlabel('Magnitude')
    plt.ylabel('Frequency')
    plt.title('Earthquake Magnitude Distribution')

    # Set X-axis ticks to label each decimal magnitude
    x_ticks = np.arange(0, max(magnitudes) + 0.1, 0.5)
    plt.xticks(x_ticks)

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plot_data = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close()

    return plot_data

def plot_disaster_magnitude_histogram(disaster_data_json, type_of_disaster):
    magnitudes = [event["geometry"][0].get("magnitudeValue") for event in disaster_data_json['events'] if type_of_disaster in event["categories"][0]["title"] and event["geometry"][0].get("magnitudeValue") is not None]

    if type_of_disaster == 'Ice':
        if not magnitudes:
            return None
            
        print(f"Ice Magnitudes: {magnitudes}")
        step_size = (max(magnitudes) - min(magnitudes)) / 20
        bins = np.arange(min(magnitudes), max(magnitudes) + step_size, len(magnitudes))

        plt.hist(magnitudes, bins=bins, color='blue')
        plt.xlabel('Magnitude (NM^2)')

        # Set X-axis ticks to label each decimal magnitude
        x_ticks = np.linspace(min(magnitudes), max(magnitudes) + step_size, 15)
        plt.xticks(x_ticks)

        y_ticks = np.arange(0, int(max(np.histogram(magnitudes, bins=bins)[0])) + 1, 1)
        plt.yticks(y_ticks)

    if type_of_disaster == 'Severe Storms':
        if not magnitudes:
            return None

        print(f"Severe Storms Magnitudes: {magnitudes}")

        bins = np.arange(min(magnitudes), max(magnitudes) + 0.1, 0.1)
        plt.hist(magnitudes, bins=bins, color='mediumseagreen')
        plt.xlabel('Magnitude (kts)')

        x_ticks = np.arange(min(magnitudes), max(magnitudes)+ 0.1, (max(magnitudes)+0.1)/10)
        plt.xticks(x_ticks)

        y_ticks = np.arange(0, int(max(np.histogram(magnitudes, bins=bins)[0])) + 1, 1)
        plt.yticks(y_ticks)

    if not magnitudes:
        # Return None if there are no magnitudes for the specified disaster type
        return None

    plt.ylabel('Frequency')
    plt.title(f'{type_of_disaster} Magnitude Distribution')

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plot_data = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close()

    return plot_data


disaster_types = ['Severe Storms', 'Ice']  # Add the specific disaster types here

# Dictionary to store the plot data for each disaster type
disaster_plots = {}

for type_of_disaster in disaster_types:
    plot_data = plot_disaster_magnitude_histogram(fetch_disaster_data(), type_of_disaster)
    if plot_data:
        disaster_plots[type_of_disaster] = plot_data

@app.route('/')
def index():
    map = create_map()
    return render_template('map.html', map=map._repr_html_())

@app.route('/visualize')
def visualize():
    quake_data_json = fetch_earthquake_data()
    earthquake_chart_data = plot_earthquake_magnitude_histogram(quake_data_json)

    # Generate plot data for each disaster type and store it in the "disaster_plots" dictionary
    disaster_types = ['Severe Storms', 'Ice']
    disaster_plots = {}

    disaster_data_json = fetch_disaster_data()

    for type_of_disaster in disaster_types:
        plot_data = plot_disaster_magnitude_histogram(disaster_data_json, type_of_disaster)
        if plot_data:
            disaster_plots[type_of_disaster] = plot_data

    return render_template('visualize.html', earthquake_chart_data=earthquake_chart_data, disaster_plots=disaster_plots)


if __name__ == '__main__':
    app.run(debug=True)