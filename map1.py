import folium
import pandas
import urllib.request
from urllib.request import Request, urlopen
import json
import webbrowser

print("The program may take about a minute to run. Please wait! The Web Map will open automatically once the program has run.")

quake_url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
qresponse = urlopen(quake_url)
quake_data_json = json.loads(qresponse.read())

m = folium.Map(titles="Stamen Terrain")

# <------------------------------------------------------>
#Adding Earthquakes in this block
fgq = folium.FeatureGroup(name="Earthquakes")
for i in quake_data_json['features']:
    quake_lat = i["geometry"]["coordinates"][1]
    quake_lon = i["geometry"]["coordinates"][0]
    place = i["properties"]["place"]
    mag = i["properties"]["mag"]
    url = "<a href="+i["properties"]["url"]+">More info here</a>"

    if mag >= 2.0:
        fgq.add_child(folium.Marker(location=[quake_lat, quake_lon],
        popup="Hazard/Area: Earthquake, %s, Magnitude: %f, Coordinates: %f,%f, %s" % (place, mag, quake_lat,quake_lon, url),
        icon=folium.Icon(color='orange')))

# <------------------------------------------------------>
#Adding other natural hazards in this block

disasters_url = Request("https://eonet.gsfc.nasa.gov/api/v3/events",
 headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'})
dresponse = urlopen(disasters_url)
disaster_data_json = json.loads(dresponse.read())


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


for i in disaster_data_json['events'][:150]:
    dis_lat = i["geometry"][0]["coordinates"][1]
    dis_lon = i["geometry"][0]["coordinates"][0]
    dis_name = i["title"]
    dis_url = "<a href="+i["sources"][0]["url"]+">More info here</a>"

    dis_type = disaster_type(i["categories"][0]["title"])

    if i["geometry"][0]["magnitudeValue"] == None:
        dis_type.add_child(folium.Marker(location=[dis_lat, dis_lon], popup="Hazard/Area: %s, Coordinates: %f, %f, %s" % (dis_name, dis_lat, dis_lon, dis_url),
        icon = folium.Icon(color=marker_color(dis_type))))
    
    else:
        dis_magV = i["geometry"][0]["magnitudeValue"]
        dis_magU = i["geometry"][0]["magnitudeUnit"]
        dis_type.add_child(folium.Marker(location=[dis_lat, dis_lon], popup="Hazard/Area: %s, Coordinates: %f, %f, Magnitude:%f %s, %s\n" % (dis_name, dis_lat, dis_lon, dis_magV, dis_magU, dis_url),
        icon = folium.Icon(color=marker_color(dis_type)))) 

# <------------------------------------------------------->

m.add_child(fgq)
m.add_child(fgd)
m.add_child(fgs)
m.add_child(fgv)
m.add_child(fgf)
m.add_child(folium.LayerControl())
m.save("DisastersWebMap.html")
webbrowser.open_new_tab('DisastersWebMap.html')

print("Finished Running!")
