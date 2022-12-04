# web page/data formatter functions
def running_page():
    with open('html/running.html') as local_file:
        content = local_file.read()
    return content

def idle_page():
    with open('html/idle.html') as local_file:
        content = local_file.read()
    return content

def settings_page():
    with open('html/settings.html') as local_file:
        content = local_file.read()
    return content


def new_config_page():
    with open('html/new_config.html') as local_file:
        content = local_file.read()
    return content

def after_config():
    with open('html/post_config.html') as local_file:
        content = local_file.read()
    return content

def dynamic_data_json(DynamicData):
    json= """{
        "MCUTemperature":""" + str(DynamicData["MCUTemperature"]) + """,
        "VBat":""" + str(DynamicData["VBat"]) + """,
        "TirePressure":""" + str(DynamicData["TirePressure"]) + """,
        "SetPressure":""" + str(DynamicData["SetPressure"]) + """,
        "Task": " """ + DynamicData["Task"] + """ ",
        "State": " """ + DynamicData["State"] + """ ",
        "Message": " """ + DynamicData["Message"] + """ "
        }"""
    
    return json

def memories_json(Settings):
    json = """
    {
        "Mem1":""" + str(Settings["Mem1"]) + """,
        "Mem2":""" + str(Settings["Mem2"]) + """,
        "Mem3":""" + str(Settings["Mem3"]) + """,
        "Mem4":""" + str(Settings["Mem4"]) + """
    }
    """

    return json

def settings_json(Settings):
    json = """
    {
        "Mem1":""" + str(Settings["Mem1"]) + """,
        "Mem2":""" + str(Settings["Mem2"]) + """,
        "Mem3":""" + str(Settings["Mem3"]) + """,
        "Mem4":""" + str(Settings["Mem4"]) + """,
        "Inflate_Valve":""" + str(Settings["Inflate_Valve"]) + """,
        "Deflate_Valve":""" + str(Settings["Deflate_Valve"]) + """,
        "P_Sensor_Offset":""" + str(Settings["P_Sensor_Offset"]) + """,
        "P_Sensor_Slope":""" + str(Settings["P_Sensor_Slope"]) + """
    }
    """

    return json

def idle_file():
    """Load the web page from the CIRCUITPY drive."""
    with open('html/idle.html') as local_file:
        content = local_file.read()
    return content
