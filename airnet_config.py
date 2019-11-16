from pathlib import Path

GCS_ADDR = ("127.0.0.1", 43211)
AIRNET_ADDR = ("127.0.0.1", 27016)
SETTINGS_FILE = Path("C:/Users/LANADA/Documents/AirSim/settings.json")

class MsgIndex(object):
	MSG_NUM = 10
	ID, POS_X, POS_Y, POS_Z, VEL_X, VEL_Y, VEL_Z, LAT, LNG, ALT = range(MSG_NUM)

class GcsMsgIndex(object):
	MSG_NUM = 4
	CMD, G_LAT, G_LNG, G_ALT = range(MSG_NUM)