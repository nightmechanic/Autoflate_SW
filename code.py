# AutoFlate
# Automatic tire inflator/deflator Conctroller code main file
# Ran Katz 2022

import time
import json
import wifi
import socketpool
import mdns
import web_pages
import ampule
import microcontroller
from binascii import crc32
import digitalio
import board
import autoflate



class ap_config_c :
    ssid = ""
    password = ""
    No_ap_config = True

current_config = ap_config_c()
new_config = ap_config_c()
counter = 0

aF = autoflate.AutoFlate()

# Digital IO setup
DIUserSW = digitalio.DigitalInOut(board.IO46)
DIUserSW.direction = digitalio.Direction.INPUT
DOFuncInd = digitalio.DigitalInOut(board.IO45)
DOFuncInd.direction = digitalio.Direction.OUTPUT




#Structs and classes
DynamicData = {
    "VBat" : 12.7,
    "MCUTemperature": 30.0,
    "TirePressure": 0.0,
    "SetPressure": 25,
    "Task": "NONE",
    "State": "IDLE",
    "Message": "OK"
}

Settings = {
    "Mem1": 15,
    "Mem2": 25,
    "Mem3": 30,
    "Mem4": 35,
    "Inflate_Valve": 0.5,
    "Deflate_Valve": 0.5,
    "P_Sensor_Offset": 0.0,
    "P_Sensor_Slope": 1.0,
    "VBat_Offset": 0.0,
    "VBat_Slope" : 1.0
}

class States:
    IDLE = "IDLE"
    RUNNING = "RUNNING"
# class Tasks:
#     NONE = "NONE"
#     MEASURING = "MEASURING"
#     INFLATING = "INFLATING"
#     DEFLATING = "DEFLATING"
#     DONE = "DONE"

currentState = States.IDLE
#currentTask  = Tasks.NONE

def load_ap_config():
    ap_config = microcontroller.nvm[0:32]
    ap_config_crc = int.from_bytes(microcontroller.nvm[32:36],"little")
    crc_check = crc32(ap_config)
    if crc_check != ap_config_crc:
        current_config.ssid = "AutoFlateDefault"
        current_config.password = "12345678"
        current_config.No_ap_config = True
        print("No valid ap_config")
    else:
        b_ssid = ap_config[0:16]
        b_password = ap_config[16:32]
        ssid_len = b_ssid.find(b'\x00')
        b_ssid = b_ssid[0:ssid_len]
        current_config.ssid = b_ssid.decode()
        password_len = b_password.find(b'\x00')
        b_password = b_password[0:password_len]
        current_config.password = b_password.decode()
        print("Valid ap_config found\n")
        print(" SSID: ", current_config.ssid, "PWD: ", current_config.password)
        current_config.No_ap_config = False

def load_settings():
    temp_settings = microcontroller.nvm[40:51]
    settings_crc = int.from_bytes(microcontroller.nvm[51:55],"little")
    crc_check = crc32(temp_settings)
    if crc_check == settings_crc:
        Settings["Mem1"] = int.from_bytes(temp_settings[0], "little")
        Settings["Mem2"] = int.from_bytes(temp_settings[1], "little")
        Settings["Mem3"] = int.from_bytes(temp_settings[2], "little")
        Settings["Mem4"] = int.from_bytes(temp_settings[3], "little")
        Settings["Inflate_Valve"] = int.from_bytes(temp_settings[4], "little") /100.0
        Settings["Deflate_Valve"] = int.from_bytes(temp_settings[5], "little") /100.0
        Settings["P_Sensor_Offset"]= int.from_bytes(temp_settings[6:10], "little", signed=True) / 1000.0
        Settings["P_Sensor_Slope"] = int.from_bytes(temp_settings[10], "little") / 100.0
        print("Saved settings loaded")
    else:
        print("Using default settings")
    return

def save_settings():
    zero = 0
    b_zero15 = zero.to_bytes(15, "little")
    microcontroller.nvm[40:55] = b_zero15
    temp_settings = zero.to_bytes(11,"little")
    temp_settings[0] = Settings["Mem1"].to_bytes(1,"little")
    temp_settings[1] = Settings["Mem2"].to_bytes(1, "little")
    temp_settings[2] = Settings["Mem3"].to_bytes(1, "little")
    temp_settings[3] = Settings["Mem4"].to_bytes(1, "little")
    value = int(Settings["Inflate_Valve"] * 100)
    temp_settings[4] = value.to_bytes(1, "little")
    value = int(Settings["Deflate_Valve"] * 100)
    temp_settings[5] = value.to_bytes(1, "little")
    value = int(Settings["P_Sensor_Offset"] * 1000)
    temp_settings[6:10] = value.to_bytes(4,"little", signed=True)
    value = int(Settings["P_Sensor_Slope"] * 100)
    temp_settings[11] = value.to_bytes(1, "little")

    microcontroller.nvm[40:51] = temp_settings
    if microcontroller.nvm[40:51] == temp_settings:
        crc = crc32(microcontroller.nvm[40:51])
        b_crc = crc.to_bytes(4, "little")
        microcontroller.nvm[51:55] = b_crc
        print("Setting saved")
    else:
        print("Couldn't save settings, value mismatch!")


    return




myhostname = "inflator"
wifi.radio.hostname = myhostname
mdnsServer = mdns.Server(wifi.radio)
mdnsServer.hostname = "inflator"

StartTime = time.monotonic()
UserIndBlink = True
while (DIUserSW.value):
    time.sleep(0.2)
    DOFuncInd.value = not DOFuncInd.value
    if (time.monotonic() - StartTime) > 5 :
        zero = 0
        b_zero36 = zero.to_bytes(36,"little")
        microcontroller.nvm[0:36] = b_zero36
        print("Long press detected, zeroing ap config")
        break

load_ap_config()
print("starting ap")
wifi.radio.start_ap(current_config.ssid, current_config.password)
pool = socketpool.SocketPool(wifi.radio)
socket = pool.socket()
socket.bind(['0.0.0.0', 80])
socket.listen(10)
socket.setblocking(False)

print("ap started")
print(str(wifi.radio.ipv4_address_ap))

print("mdns hostname:", mdnsServer.hostname )
headers = {"Content-Type": "html"}

@ampule.route("/")
def base(request):
    print("main route called")
    if current_config.No_ap_config:
        return (200, {"Content-Type": "html"}, web_pages.new_config_page())
    elif currentState == States.IDLE:
        return (200, {"Content-Type": "html"}, web_pages.idle_page())
    else:
        return (200, {"Content-Type": "html"}, web_pages.running_page())

@ampule.route("/start")
def base(request):
    print("start route called")
    global currentState
    if (current_config.No_ap_config or currentState == States.RUNNING):
        return (400, {}, "Bad Request")
    else:
        currentState=States.RUNNING
        return (200, {"Content-Type": "html"}, web_pages.running_page())

@ampule.route("/stop")
def base(request):
    print("stop route called")
    global currentState
    if (current_config.No_ap_config or currentState == States.IDLE):
        return (400, {}, "Bad Request")
    else:
        currentState=States.IDLE
        return (200, {"Content-Type": "html"}, web_pages.main_page())

@ampule.route("/idle")
def base(request):
    if (current_config.No_ap_config or currentState == States.RUNNING):
        return (400, {}, "Bad Request")
    else:
        print("idle route called")
        return (200, {"Content-Type": "html"}, web_pages.idle_file())

@ampule.route("/new_config_input")
def base(request):
    if current_config.No_ap_config:
        print("new config input called")
        new_config.ssid = request.params["SSID"]
        new_config.password = request.params["pwd"]
        print(new_config.ssid, "  ", new_config.password)
        return (200, {"Content-Type": "html"}, web_pages.after_config())
    else:
        return (400, {}, "Bad Request")

@ampule.route("/get_dynamic_data")
def base(request):
    if current_config.No_ap_config:
        return (400, {}, "Bad Request")
    else:
        print("get dynamic data called")
        return (200, {"Content-Type": "application/json; charset=UTF-8"}, web_pages.dynamic_data_json(DynamicData))

@ampule.route("/get_memories")
def base(request):
    if current_config.No_ap_config:
        return (400, {}, "Bad Request")
    else:
        print("get memories called")
        return (200, {"Content-Type": "application/json; charset=UTF-8"}, web_pages.memories_json(Settings))

@ampule.route("/get_settings")
def base(request):
    if (current_config.No_ap_config or currentState == States.RUNNING):
        return (400, {}, "Bad Request")
    else:
        print("get dynamic data called")
        return (200, {"Content-Type": "application/json; charset=UTF-8"}, web_pages.settings_json(Settings))

@ampule.route("/set_pressure", method='POST')
def base(request):
    if (current_config.No_ap_config or currentState == States.RUNNING):
        return (400, {}, "Bad Request")
    else:
        print("set pressure called")
        json_data = json.loads(request.body)
        DynamicData["SetPressure"] = int(json_data["pressure"])
        print(DynamicData["SetPressure"])
        return (200, {}, "Pressure Updated")

@ampule.route("/set_settings", method='POST')
def base(request):
    if current_config.No_ap_config or currentState == States.RUNNING:
        return (400, {}, "Bad Request")
    else:
        print("set settings called")
        json_data = json.loads(request.body)
        Settings["Mem1"] = int(json_data["mem1"])
        Settings["Mem2"] = int(json_data["mem2"])
        Settings["Mem3"] = int(json_data["mem3"])
        Settings["Mem4"] = int(json_data["mem4"])
        Settings["Inflate_Valve"] = float(json_data["inflate_valve"])
        Settings["Deflate_Valve"] = float(json_data["deflate_valve"])
        Settings["P_Sensor_Offset"] = float(json_data["press_offset"])
        Settings["P_Sensor_Slope"] = float(json_data["press_slope"])
        save_settings()
        print(Settings)
        return (200, {"Content-Type": "html"}, web_pages.idle_page())

@ampule.route("/settings")
def base(request):
    if (current_config.No_ap_config or currentState == States.RUNNING):
        return (400, {}, "Bad Request")
    else:
        print("settings called")
        return (200, {"Content-Type": "html"}, web_pages.settings_page())

def update_apconfig():
    zero = 0
    b_zero36 = zero.to_bytes(36,"little")
    microcontroller.nvm[0:36] = b_zero36

    b_ssid = bytearray(new_config.ssid)
    ssid_len = len(b_ssid)

    while (ssid_len < 16):
        b_ssid.append(0)
        ssid_len = ssid_len + 1

    microcontroller.nvm[0:16] = b_ssid

    b_password= bytearray(new_config.password)
    password_len = len(b_password)

    while (password_len < 16):
        b_password.append(0)
        password_len = password_len + 1

    microcontroller.nvm[16:32] = b_password

    crc = crc32(microcontroller.nvm[0:32])
    b_crc = crc.to_bytes(4,"little")
    microcontroller.nvm[32:36] = b_crc

    print("new ap_config written")

def update_dynamic_data(pressure):
    DynamicData["MCUTemperature"] = round(microcontroller.cpu.temperature, 1)
    DynamicData["VBat"] = aF.get_VBat()
    DynamicData["State"] = currentState
    if pressure:
        DynamicData["TirePressure"] = aF.get_pressure()
    return


max_diff = 0
diff_avg = 0
diff_counter = 0
if current_config.No_ap_config:
    UserIndBlink = False

load_settings()

while True:
    DOFuncInd.value = True
    time.sleep(0.5)
    ampule.poll(socket)
    if ( current_config.No_ap_config and new_config.ssid != "" ):
        update_apconfig()
        microcontroller.on_next_reset(microcontroller.RunMode.NORMAL)
        microcontroller.reset()

    if UserIndBlink:
        DOFuncInd.value = not DOFuncInd.value

    if currentState == States.IDLE:
        update_dynamic_data(True)
    elif currentState == States.RUNNING:
        update_dynamic_data(False)
        DynamicData["TirePressure"], DynamicData["Task"], DynamicData["Message"] = \
            aF.inflate_deflate(DynamicData["SetPressure"])

    if DynamicData["Task"] == aF.Tasks.DONE :
        currentState = States.IDLE



    counter = counter + 1

    if counter > 10:
        print("polling....")
        print("ADS voltage is: ", aF.adsVref.voltage)
        print(currentState, DynamicData )
        counter = 0

    # tempVal = 0
    # for x in range(8):
    #     tempVal = tempVal+ aF.AIVref.value
    # tempVal = tempVal*3.288/(8*65536)
    # diff = (tempVal - aF.adsVref.voltage) * 1000
    # print("CPU temp: %s Pressure: %spsi, Vref: %smv, Vbat: %smV, UserSW: %s"
    #       %(microcontroller.cpu.temperature, aF.get_pressure(), aF.adsVref.voltage, aF.get_VBat(), DIUserSW.value))

