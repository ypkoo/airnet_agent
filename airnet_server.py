import airsim
from airnet_config import * 
import socket, threading, time, json, select, datetime
import msgpack



class AirnetServer(threading.Thread):

    def __init__(self, client, lock, vehicles):
        super(AirnetServer, self).__init__()

        self.lock = lock
        self.client = client
        self.vehicles = vehicles
        self.agents = []

        self.alive = threading.Event()
        self.alive.set()


    def run(self):
        self.socket_init()

        while self.alive.isSet():
            conn, addr = self.sock.accept()

            data = conn.recv(16)
            drone_id = msgpack.unpackb(data)
            drone_name = "Drone" + str(drone_id[0])

            print("[Airnet Server] new connection: %s" % drone_name)

            agent = AirnetAgent(self.client, drone_name, self.lock, conn, self.vehicles[drone_name])
            agent.start()

            self.agents.append(agent)


        for agent in self.agents:
            print("clear airnet agent")
            agent.alive.clear()

        self.sock.close()


    def socket_init(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.sock.bind(AIRNET_ADDR)
        self.sock.listen(10)





class AirnetAgent(threading.Thread):

    def __init__(self, client, name, lock, sock, init_pos):
        super(AirnetAgent, self).__init__()
        self.lock = lock
        self.id = name[-1]
        self.name = name
        self.client = client
        self.init_pos = init_pos
        self.sock = sock
        self.alive = threading.Event()
        self.alive.set()

    def run(self):

        while self.alive.isSet():
            time.sleep(.5)
            msg = self.build_msg()
            # print(self.name, msg)
            msg_packed = msgpack.packb(msg, use_bin_type=True)
            self.sock.send(msg_packed)

        self.sock.close()

    def build_msg(self):
        self.lock.acquire()
        state = self.client.getMultirotorState(vehicle_name=self.name)
        # kinematics = self.client.simGetGroundTruthKinematics(vehicle_name=self.name)
        # gps = self.client.getGpsData(vehicle_name=self.name)
        self.lock.release()

        gps = state.gps_location
        kinematics = state.kinematics_estimated
        pos = kinematics.position
        vel = kinematics.linear_velocity

        msg = [0] * MsgIndex.MSG_NUM

        msg[MsgIndex.ID] = int(self.id)

        msg[MsgIndex.POS_X] = pos.x_val + self.init_pos["X"]
        msg[MsgIndex.POS_Y] = pos.y_val + self.init_pos["Y"]
        msg[MsgIndex.POS_Z] = pos.z_val + self.init_pos["Z"]

        msg[MsgIndex.VEL_X] = vel.x_val
        msg[MsgIndex.VEL_Y] = vel.y_val
        msg[MsgIndex.VEL_Z] = vel.z_val
        
        msg[MsgIndex.LAT] = gps.latitude
        msg[MsgIndex.LNG] = gps.longitude
        msg[MsgIndex.ALT] = gps.altitude

        return msg

if __name__ == "__main__":

    lock = threading.Lock()

    airnet_server = AirnetServer(lock)

    airnet_server.start()