# packages
from lib_class_Ambient import Ambient
from lib_class_Building import BuildingEx
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
           "temp_wall": 18.0,
           "temp_ins": 16.0,
           "temp_ex": 20.0,
           "temp_eh": 5.5,
           "air_AQ": 1060.0,
           "air_PB": 0.0,
           "wall_AQ": 45000,
           "wall_PB": 0.0,
           "ins_AQ": 1300.0,
           "ins_PB": 0.0,
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
           "dust_depo": 0.0,
           "filt_su_pres": 1.1,
           "filt_ex_pres": 1.2,
           "air_q": 456.0}


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

building = BuildingEx()
building.config = load_config(building.config_path)
building.initialize_params()

while hrs < 168:
    if (sec % 3600) == 0:
        ambient.renew_forecast()
    if (sec % 600) == 0:
        ambient.renew_dust_measure()

    trig = False
    while not trig:
        time.sleep(0.100)
        trig, hrs, sec = data_handler.timer(3)  # Timer triggers script execution in adjustable steps, 3s for example.

    op_data["ti_diff"] = data_handler.ti_diff()

    print("  Elapsed: {}hrs, {}sec, ti_diff: {:.4}, people: ".format(hrs, sec, op_data["ti_diff"] * 3600), end="")
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

    power_source = building.power_delivery(op_data)

    air_conditions = building.calculate_layer("air", op_data, power_source, op_data["temp_wall"])
    op_data["air_AQ"] = air_conditions["AQ"]
    op_data["air_PB"] = air_conditions["PB"]
    op_data["temp_rm"] = op_data["temp_ex"] = air_conditions["temperature"]

    wall_conditions = building.calculate_layer("wall", op_data, air_conditions["power_sink"], op_data["temp_ins"])
    op_data["wall_AQ"] = wall_conditions["AQ"]
    op_data["wall_PB"] = wall_conditions["PB"]
    op_data["temp_wall"] = wall_conditions["temperature"]

    insulation_conditions = building.calculate_layer("ins", op_data, wall_conditions["power_sink"] , op_data["temp"])
    op_data["ins_AQ"] = insulation_conditions["AQ"]
    op_data["ins_PB"] = insulation_conditions["PB"]
    op_data["temp_ins"] = insulation_conditions["temperature"]

    op_data["air_q"] = building.simulate_dioxide(op_data)

    print("solar: {:.4}, power_src: {:.6}, temp_rm: {:.4}, temp_wall: {:.4}, temp_ins: {:.4}".
          format(op_data["solar"], power_source, op_data["temp_rm"], op_data["temp_wall"], op_data["temp_ins"]))

    model_values = controls.calculate(op_data)
    for key in model_values:
        op_data[key] = model_values[key]

    controls.write_json({"temp": [op_data["temp"], 0],
                         "temp_su": [op_data["temp_su"], 0],
                         "temp_rm": [op_data["temp_rm"], 0],
                         "temp_ex": [op_data["temp_ex"], 0],
                         "temp_eh": [op_data["temp_eh"], 0],
                         "flow_su": [op_data["flow_su"], 0],
                         "flow_ex": [op_data["flow_ex"], 0],
                         "filt_su_pres": [op_data["filt_su_pres"], 0],
                         "filt_ex_pres": [op_data["filt_ex_pres"], 0],
                         "air_q": [op_data["air_q"], 2]})

    if (sec % 60) == 0:
        data_handler.store_op_data(op_data)
        data_handler.dump_to_file(op_data)
        if "error" in op_data.keys():
            op_data.pop("error")
