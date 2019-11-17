import airsim
from airnet_config import * 
import socket, threading, time, json, select, datetime
import msgpack
from math import sqrt



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

            agent = AirnetAgent(self.client, drone_name, self.lock, conn, self.vehicles)
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

    def __init__(self, client, name, lock, sock, vehicles):
        super(AirnetAgent, self).__init__()
        self.lock = lock
        self.id = name[-1]
        self.name = name
        self.client = client
        self.vehicles = vehicles
        self.initPos = vehicles[self.name]
        self.sock = sock
        self.alive = threading.Event()
        self.alive.set()

    def run(self):
        self.multirotor_init()

        while self.alive.isSet():
            time.sleep(.5)
            msg = self.build_msg()
            # print(self.name, msg)
            msg_packed = msgpack.packb(msg, use_bin_type=True)
            self.sock.send(msg_packed)
            # print("[Airnet agent %s]" % self.id, "msg sent:", msg)

            ready = select.select([self.sock], [], [], 0.1)
            if ready[0]:
                data = self.sock.recv(2048)
                data_unpacked = msgpack.unpackb(data)
                print ("[Airnet agent %s]" % self.id, "received data: ", data_unpacked)

                cmd = data_unpacked[GcsMsgIndex.CMD]
                self.process_command(cmd)

            else:
                continue

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

        msg = [0] * MsgIndex.IDX_NUM

        msg[MsgIndex.ID] = int(self.id)

        msg[MsgIndex.POS_X] = pos.x_val + self.initPos["X"]
        msg[MsgIndex.POS_Y] = pos.y_val + self.initPos["Y"]
        msg[MsgIndex.POS_Z] = pos.z_val + self.initPos["Z"]

        msg[MsgIndex.VEL_X] = vel.x_val
        msg[MsgIndex.VEL_Y] = vel.y_val
        msg[MsgIndex.VEL_Z] = vel.z_val
        
        msg[MsgIndex.LAT] = gps.latitude
        msg[MsgIndex.LNG] = gps.longitude
        msg[MsgIndex.ALT] = gps.altitude

        return msg

    def multirotor_init(self):
        self.lock.acquire()
        self.client.enableApiControl(True, self.name)
        self.client.armDisarm(True, self.name)
        self.lock.release()

    def process_command(self, cmd):
        if cmd == CMDIndex.TAKEOFF:

            self.lock.acquire()
            self.client.takeoffAsync(vehicle_name=self.name)
            self.lock.release()
        elif cmd == CMDIndex.MOVE:
            initPosX = int(self.initPos["X"])
            initPosY = int(self.initPos["Y"])
            distFromZero = sqrt(initPosX**2 + initPosY**2)

            vel = 5
            velX = vel * (initPosX / distFromZero)
            velY = vel * (initPosY / distFromZero)

            self.lock.acquire()
            self.client.moveByVelocityAsync(velX, velY, 0, duration=3, vehicle_name=self.name)

            self.lock.release()
        elif cmd == CMDIndex.LAND:
            self.lock.acquire()
            self.client.landAsync(vehicle_name=self.name)
            self.lock.release()
        elif cmd == CMDIndex.GOHOME:
            self.lock.acquire()
            self.client.goHomeAsync(vehicle_name=self.name)
            self.lock.release()

        elif cmd == CMDIndex.GOFORWARD:
            self.lock.acquire()
            self.client.moveByVelocityAsync(5, 0, 0, duration=3, drivetrain = DrivetrainType.ForwardOnly, vehicle_name=self.name)
            self.lock.release()
        elif cmd == CMDIndex.STOP:
            self.lock.acquire()
            self.client.moveByVelocityAsync(0, 0, 0, duration=3, vehicle_name=self.name)
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

if __name__ == "__main__":

    lock = threading.Lock()

    airnet_server = AirnetServer(lock)

    airnet_server.start()