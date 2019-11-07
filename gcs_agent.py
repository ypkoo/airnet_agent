import airsim
import socket, threading, time, json, select, datetime
import pprint
from pathlib import Path

ADDR = ("127.0.0.1", 43211)
SETTINGS_FILE = Path("C:/Users/LANADA/Documents/AirSim/settings.json")

class GCSAgent(threading.Thread):

    def __init__(self, client, name, lock):
        super(GCSAgent, self).__init__()
        self.lock = lock
        self.id = name[-1]
        self.name = name
        self.client = client
        self.alive = threading.Event()
        self.alive.set()

    def run(self):
        self.socket_init()
        self.multirotor_init()

        while self.alive.isSet():
            time.sleep(.3)
            status = self.get_status()
            self.s.send(json.dumps(status).encode())
            # recv_data = self.s.recv(2048)
            # print "data sent: ", data
            ready = select.select([self.s], [], [], 0.1)
            if ready[0]:
                recv_data = json.loads(self.s.recv(2048))
                print ("received data: ", recv_data)

                cmd = recv_data["command"]
                self.process_command(cmd)

            else:
                continue
        self.s.close()

    def socket_init(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect(ADDR)
        self.s.setblocking(0)
        # self.s.settimeout(.2)
        print ("connected to", ADDR)

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
            print(self.name, "start!")
        elif cmd == "land":
            print(self.name, "land!")

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
        data = json.load(settings)
        drones = data["Vehicles"].keys()

    client = airsim.MultirotorClient()
    client.confirmConnection()

    lock = threading.Lock()

    agents = []

    for drone in drones:
        agent = GCSAgent(client, drone, lock)
        agents.append(agent)
        agent.start()

    try:
        while True:
            time.sleep(.1)
    except KeyboardInterrupt:
        print ("KeyboardInterrupt")

        for agent in agents:
            agent.alive.clear()
