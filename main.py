import os
from flask import Flask, render_template
import folium
import json
import urllib.request
from urllib.request import Request, urlopen
from deta import Deta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import numpy as np
from datetime import datetime, timedelta

app = Flask(__name__)

# Set MPLCONFIGDIR to a writable directory
os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib'
matplotlib.use('Agg')

# Initialize Deta
deta = Deta()

# Connect to or create Deta Bases
earthquake_db = deta.Base("earthquake_data")
disaster_db = deta.Base("disaster_data")

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
    
def chunk_data(data, chunk_size=100):
    """Split data into chunks of specified size."""
    return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

def fetch_and_store_data():
    # Fetch earthquake data
    quake_url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
    qresponse = urllib.request.urlopen(quake_url)
    quake_data_json = json.loads(qresponse.read())
    
    # Store earthquake data in Deta Base
    quake_chunks = chunk_data(quake_data_json['features'])
    earthquake_db.put({"key": "metadata", "timestamp": datetime.now().isoformat(), "chunk_count": len(quake_chunks)})
    for i, chunk in enumerate(quake_chunks):
        earthquake_db.put({"key": f"chunk_{i}", "data": chunk})

    # Fetch disaster data
    disasters_url = Request(
        "https://eonet.gsfc.nasa.gov/api/v3/events",
        headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}
    )
    dresponse = urlopen(disasters_url)
    disaster_data_json = json.loads(dresponse.read())
    
    # Store disaster data in Deta Base
    disaster_chunks = chunk_data(disaster_data_json['events'])
    disaster_db.put({"key": "metadata", "timestamp": datetime.now().isoformat(), "chunk_count": len(disaster_chunks)})
    for i, chunk in enumerate(disaster_chunks):
        disaster_db.put({"key": f"chunk_{i}", "data": chunk})

def get_stored_data():
    earthquake_metadata = earthquake_db.get("metadata")
    disaster_metadata = disaster_db.get("metadata")
    
    if not earthquake_metadata or not disaster_metadata:
        fetch_and_store_data()
        earthquake_metadata = earthquake_db.get("metadata")
        disaster_metadata = disaster_db.get("metadata")
    
    earthquake_data = {'features': []}
    for i in range(earthquake_metadata['chunk_count']):
        chunk = earthquake_db.get(f"chunk_{i}")
        earthquake_data['features'].extend(chunk['data'])

    disaster_data = {'events': []}
    for i in range(disaster_metadata['chunk_count']):
        chunk = disaster_db.get(f"chunk_{i}")
        disaster_data['events'].extend(chunk['data'])
    
    return earthquake_data, disaster_data

def create_map(quake_data_json, disaster_data_json):
    m = folium.Map(location=[0, 0], zoom_start=2)

    # Adding Earthquakes
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
            popup="Hazard/Area: Earthquake, %s, \nMagnitude: %f, \nCoordinates: %f,%f, %s" % (place, mag, quake_lat,quake_lon, url),
            icon=folium.Icon(color='orange')))

    # Adding other natural hazards
    print("Parsing data on other disasters...")
    for i in disaster_data_json['events'][:500]:
        dis_lat = i["geometry"][0]["coordinates"][1]
        dis_lon = i["geometry"][0]["coordinates"][0]
        dis_name = i["title"]
        dis_url = '<a href="' + i["sources"][0]["url"] + '" target="_blank">More info here</a>'

        dis_type = disaster_type(i["categories"][0]["title"])

        if "magnitudeValue" not in i["geometry"][0] or i["geometry"][0]["magnitudeValue"] is None:
            dis_type.add_child(folium.Marker(location=[dis_lat, dis_lon], popup="Hazard/Area: %s, \nCoordinates: %f, %f, %s" % (dis_name, dis_lat, dis_lon, dis_url),
            icon = folium.Icon(color=marker_color(dis_type))))
        
        else:
            dis_magV = i["geometry"][0]["magnitudeValue"]
            dis_magU = i["geometry"][0]["magnitudeUnit"]
            dis_type.add_child(folium.Marker(location=[dis_lat, dis_lon], popup="Hazard/Area: %s, \nCoordinates: %f, %f, \nMagnitude:%f %s, %s\n" % (dis_name, dis_lat, dis_lon, dis_magV, dis_magU, dis_url),
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


# disaster_types = ['Severe Storms', 'Ice']  # Add the specific disaster types here

# # Dictionary to store the plot data for each disaster type
# disaster_plots = {}

# for type_of_disaster in disaster_types:
#     plot_data = plot_disaster_magnitude_histogram(fetch_disaster_data(), type_of_disaster)
#     if plot_data:
#         disaster_plots[type_of_disaster] = plot_data

@app.route('/')
def index():
    quake_data_json, disaster_data_json = get_stored_data()
    map = create_map(quake_data_json, disaster_data_json)
    return render_template('map.html', map=map._repr_html_())

@app.route('/visualize')
def visualize():
    quake_data_json, disaster_data_json = get_stored_data()
    earthquake_chart_data = plot_earthquake_magnitude_histogram(quake_data_json)

    disaster_types = ['Severe Storms', 'Ice']
    disaster_plots = {}

    for type_of_disaster in disaster_types:
        plot_data = plot_disaster_magnitude_histogram(disaster_data_json, type_of_disaster)
        if plot_data:
            disaster_plots[type_of_disaster] = plot_data

    return render_template('visualize.html', earthquake_chart_data=earthquake_chart_data, disaster_plots=disaster_plots)

@app.route('/__space/v0/actions', methods=['POST'])
def handle_scheduled_action():
    print("triggering fetch_and_store_data")
    fetch_and_store_data()
    print("succesfully invoked fetch_and_store")
    return '', 204

if __name__ == '__main__':
    app.run(debug=True)