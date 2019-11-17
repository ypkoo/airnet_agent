from pathlib import Path

GCS_ADDR = ("127.0.0.1", 43211)
GCS_PROXY_ADDR = ("127.0.0.1", 43212)
AIRNET_ADDR = ("127.0.0.1", 27016)
SETTINGS_FILE = Path("C:/Users/LANADA/Documents/AirSim/settings.json")

class MsgIndex(object):
	IDX_NUM = 10
	ID, POS_X, POS_Y, POS_Z, VEL_X, VEL_Y, VEL_Z, LAT, LNG, ALT = range(IDX_NUM)

class GcsMsgIndex(object):
	IDX_NUM = 4
	CMD, G_LAT, G_LNG, G_ALT = range(IDX_NUM)

class CMDIndex(object):
	IDX_NUM = 6
	TAKEOFF, MOVE, LAND, GOHOME, GOFORWARD, STOP = range(IDX_NUM)

