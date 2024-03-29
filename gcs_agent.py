import airsim
import socket, threading, time, json, select, datetime
import pprint
from pathlib import Path
from airnet_config import * 
from math import sqrt


class GCSAgent(threading.Thread):

    def __init__(self, client, name, lock, vehicles):
        super(GCSAgent, self).__init__()
        self.lock = lock
        self.id = name[-1]
        self.name = name
        self.client = client
        self.vehicles = vehicles # for reset
        self.alive = threading.Event()
        self.alive.set()

    def run(self):
        self.socket_init()
        self.multirotor_init()

        while self.alive.isSet():
            time.sleep(.3)
            status = self.get_status()
            self.sock.send(json.dumps(status).encode())
            ready = select.select([self.sock], [], [], 0.1)
            if ready[0]:
                recv_data = json.loads(self.sock.recv(2048))
                print (self.name, "received data: ", recv_data)

                cmd = recv_data["command"]
                self.process_command(cmd)

            else:
                continue
        self.sock.close()

    def socket_init(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(GCS_ADDR)
        self.sock.setblocking(0)
        # self.sock.settimeout(.2)
        print ("connected to", GCS_ADDR)

    def multirotor_init(self):
        self.lock.acquire()
        self.client.enableApiControl(True, self.name)
        self.client.armDisarm(True, self.name)
        self.lock.release()

    def process_command(self, cmd):
        if cmd == "takeoff":
            self.lock.acquire()
            self.client.takeoffAsync(vehicle_name=self.name)
            self.lock.release()
        elif cmd == "start":
            initPosX = int(self.vehicles[self.name]["X"])
            initPosY = int(self.vehicles[self.name]["Y"])
            distFromZero = sqrt(initPosX**2 + initPosY**2)

            vel = 5
            velX = vel * (initPosX / distFromZero)
            velY = vel * (initPosY / distFromZero)

            self.lock.acquire()
            self.client.moveByVelocityAsync(velX, velY, 0, duration=3, vehicle_name=self.name)

            self.lock.release()
        elif cmd == "land":
            self.lock.acquire()
            self.client.landAsync(vehicle_name=self.name)
            self.lock.release()
        elif cmd == "goHome":
            self.lock.acquire()
            self.client.goHomeAsync(vehicle_name=self.name)
            self.lock.release()
        elif cmd == "reset":
            # if I'm the first drone, do reset. Otherwise, do nothing.
            if self.name == list(self.vehicles.keys())[0]:
                print(self.name, "reset!")
                self.lock.acquire()
                self.client.reset()

                # enableApiControl should be done after reset. 
                for drone in list(self.vehicles.keys()):
                    self.client.enableApiControl(True, drone)
                    self.client.armDisarm(True, drone)
                self.lock.release()


    def get_status(self):
        self.lock.acquire()
        state = self.client.getMultirotorState(vehicle_name=self.name)
        self.lock.release()

        gps = state.gps_location

        data = {
                "type": "status",
                "data": {
                    "id": self.id,
                    "lat": gps.latitude,
                    "lng": gps.longitude,
                    "alt": gps.altitude,
                    "activate": "on",
                    "battery": "95",
                    "yaw": "45.0",
                    "state": "ready",
                    "lastUpdate": str(datetime.datetime.now()),
                },
            }

        return data


if __name__ == "__main__":

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


    try:
        while True:
            time.sleep(.1)
    except KeyboardInterrupt:
        print ("KeyboardInterrupt")

        for agent in agents:
            agent.alive.clear()
