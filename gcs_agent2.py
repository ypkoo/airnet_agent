import airsim
import socket, threading, time, json, select, datetime
import pprint
import msgpack
from pathlib import Path
from airnet_config import * 
from math import sqrt

class GCSServer(threading.Thread):

    def __init__(self, vehicles):
        super(GCSServer, self).__init__()

        self.vehicles = vehicles
        self.agents = []

        self.alive = threading.Event()
        self.alive.set()


    def run(self):
        self.socket_init()

        while self.alive.isSet():
            conn, addr = self.sock.accept()

            data = conn.recv(2048)
            data_unpacked = msgpack.unpackb(data)
            drone_name = "Drone" + str(data_unpacked[MsgIndex.ID])

            print("[GCS Proxy Server] new connection: %s" % drone_name)

            agent = GCSAgent(drone_name, conn, self.vehicles[drone_name])
            agent.start()

            self.agents.append(agent)


        for agent in self.agents:
            print("clear airnet agent")
            agent.alive.clear()

        self.sock.close()


    def socket_init(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.sock.bind(GCS_PROXY_ADDR)
        self.sock.listen(10)


class GCSAgent(threading.Thread):

    def __init__(self, name, proxySock, vehicles):
        super(GCSAgent, self).__init__()

        self.id = name[-1]
        self.name = name
        self.proxySock = proxySock
        self.vehicles = vehicles # for reset
        self.msg = None
        self.alive = threading.Event()
        self.alive.set()

    def run(self):
        self.socket_init()

        while self.alive.isSet():

            time.sleep(.5)

            if self.msg:
                # print("[GCS agent %s]" % self.id, "send to GCS server", self.msg)
                self.sock.send(json.dumps(self.msg).encode())


            read_sockets, _, _ = select.select([self.proxySock, self.sock], [], [], 0.1)
            for s in read_sockets:
                if s is self.proxySock:

                    data = self.proxySock.recv(2048)
                    # print("[GCS agent %s]" % self.id, "received data:", data)
                    data_unpacked = msgpack.unpackb(data)
                    # print (self.name, "received data: ", data_unpacked)

                    self.msg = self.build_msg(data_unpacked)
                    # print("[GCS agent %s]" % self.id, self.msg)

                elif s is self.sock:
                    data = json.loads(self.sock.recv(2048))
                    print("[GCS agent %s]" % self.id, "received data:", data)

                    cmdMsg = self.build_cmd_msg(data)
                    self.proxySock.send(msgpack.packb(cmdMsg))

        self.proxySock.close()
        self.sock.close()

    def socket_init(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(GCS_ADDR)
        self.sock.setblocking(0)
        # self.sock.settimeout(.2)
        print ("[GCS agent %s]" % self.id, "connected to", GCS_ADDR)

    def build_msg(self, msg):

        data = {
                "type": "status",
                "data": {
                    "id": self.id,
                    "lat": msg[MsgIndex.LAT],
                    "lng": msg[MsgIndex.LNG],
                    "alt": msg[MsgIndex.ALT],
                    "activate": "on",
                    "battery": "95",
                    "yaw": "45.0",
                    "state": "ready",
                    "lastUpdate": str(datetime.datetime.now()),
                },
            }

        return data

    def build_cmd_msg(self, msg):

        cmdMsg = [0] * GcsMsgIndex.IDX_NUM

        if msg["command"] == "takeoff": 
            cmdMsg[GcsMsgIndex.CMD] = CMDIndex.TAKEOFF
        elif msg["command"] == "move": 
            cmdMsg[GcsMsgIndex.CMD] = CMDIndex.MOVE
        elif msg["command"] == "land": 
            cmdMsg[GcsMsgIndex.CMD] = CMDIndex.LAND
        elif msg["command"] == "goHome": 
            cmdMsg[GcsMsgIndex.CMD] = CMDIndex.GOHOME
        elif msg["command"] == "goForward": 
            cmdMsg[GcsMsgIndex.CMD] = CMDIndex.GOFORWARD
        elif msg["command"] == "stop": 
            cmdMsg[GcsMsgIndex.CMD] = CMDIndex.STOP


        # msg[GcsMsgIndex.G_LAT] = 

        return cmdMsg


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
