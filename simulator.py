# packages
from lib_class_Ambient import Ambient
from lib_class_Building import Building
from lib_class_Climatix import Climatix
from lib_class_other import Handler, load_config
import time


# defs
# Future plan: use database to store operating data, instead of using global variable.
op_data = {"temp": 10.0,
           "preci": 0.0,
           "solar": 0.0,
           "dust": 0.0,
           "ti_diff": 0.0,
           "temp_su": 20.0,
           "temp_rm": 20.0,
           "temp_con": 18.0,
           "temp_ins": 16.0,
           "temp_ex": 20.0,
           "damp_cmd": True,
           "flow_su": 0.0,
           "flow_ex": 0.0,
           "hrec_pos": 0.0,
           "hrec_pwr": 0.0,
           "pump_cmd": True,
           "htg_pos": 0.0,
           "htg_pwr": 0.0,
           "clg_cmd": True,
           "clg_pos": 0.0,
           "clg_pwr": 0.0,
           "dust_depo": 0.0}


# const
# All constants stored in TXT files


# code
ambient = Ambient()
ambient.config = load_config(ambient.config_path)
ambient.create_meteo_headers()
ambient.get_coordinates()

controls = Climatix()
controls.config = load_config(controls.config_path)
controls.climatix_auth()
# 1st time initialization, to start from good values, not from zeros
control_values = controls.read_json(["damp_cmd",
                                     "fan_su_cmd",
                                     "fan_su_pos",
                                     "flow_su",
                                     "fan_ex_cmd",
                                     "fan_ex_pos",
                                     "flow_ex",
                                     "hrec_pos",
                                     "pump_cmd",
                                     "htg_pos",
                                     "clg_cmd",
                                     "clg_pos",
                                     "temp",
                                     "temp_su",
                                     "temp_rm",
                                     "air_q"])

for key in control_values:
    op_data[key] = control_values[key]

data_handler = Handler()
op_data = data_handler.recover_op_data(op_data)
hrs = sec = 0

building = Building(op_data["temp_rm"], op_data["temp_con"], op_data["temp_ins"])
building.config = load_config(building.config_path)

while hrs < 168:
    if (sec % 3600) == 0:
        ambient.renew_forecast()
    if (sec % 600) == 0:
        ambient.renew_dust_measure()

    trig = False
    while not trig:
        time.sleep(0.100)
        trig, hrs, sec = data_handler.timer(3)  # Timer triggers script execution in adjustable steps, 3s for example.

    print("  Elapsed: {}hrs, {}sec, ".format(hrs, sec), end="")
    outside_conditions = ambient.simulate()
    for key in ["temp", "preci", "solar", "dust"]:
        op_data[key] = outside_conditions[key]

    control_values = controls.read_json(["damp_cmd",
                                         "fan_su_cmd",
                                         "fan_su_pos",
                                         "fan_ex_cmd",
                                         "fan_ex_pos",
                                         "hrec_pos",
                                         "pump_cmd",
                                         "htg_pos",
                                         "clg_cmd",
                                         "clg_pos"])
    for key in control_values:
        op_data[key] = control_values[key]

    internal_conditions = building.calculate(op_data)
    print(internal_conditions)
    for key in internal_conditions:
        op_data[key] = internal_conditions[key]

    model_values = controls.calculate(op_data)
    print(model_values)
    for key in model_values:
        op_data[key] = model_values[key]

    controls.write_json({"temp": [op_data["temp"], False],
                         "temp_su": [op_data["temp_su"], False],
                         "temp_rm": [op_data["temp_rm"], False],
                         "flow_su": [op_data["flow_su"], False],
                         "flow_ex": [op_data["flow_ex"], False]})

    if (sec % 60) == 0:
        data_handler.store_op_data(op_data)
        data_handler.dump_to_file(op_data)
        if "error" in op_data.keys():
            op_data.pop("error")
