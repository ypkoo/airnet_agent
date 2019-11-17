from airnet_server2 import AirnetServer
from gcs_agent2 import GCSServer
from airnet_config import *
import json, threading, time
import airsim


with open(SETTINGS_FILE) as settings:
    vehicles = json.load(settings)["Vehicles"]

print("[Airnet]", "connecting to airsim client...")
client = airsim.MultirotorClient()
client.confirmConnection()

lock = threading.Lock()


gcs_proxy_server = GCSServer(vehicles)
gcs_proxy_server.start()
airnet_server = AirnetServer(client, lock, vehicles)
airnet_server.start()

try:
    while True:
        time.sleep(.1)
except KeyboardInterrupt:
    print ("KeyboardInterrupt")

    gcs_proxy_server.alive.clear()
    airnet_server.alive.clear()