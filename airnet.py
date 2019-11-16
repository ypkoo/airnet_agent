from airnet_server import AirnetServer
from gcs_agent import GCSAgent
from airnet_config import *
import json, threading, time
import airsim


with open(SETTINGS_FILE) as settings:
    vehicles = json.load(settings)["Vehicles"]
    drones = list(vehicles.keys())

client = airsim.MultirotorClient()
client.confirmConnection()

lock = threading.Lock()

agents = []

for drone in drones:
    agent = GCSAgent(client, drone, lock, vehicles)
    agents.append(agent)
    agent.start()

airnet_server = AirnetServer(client, lock, vehicles)
airnet_server.start()

try:
    while True:
        time.sleep(.1)
except KeyboardInterrupt:
    print ("KeyboardInterrupt")

    for agent in agents:
        agent.alive.clear()

    airnet_server.alive.clear()