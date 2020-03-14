# packages
from lib_class import Ambient, Building, Climatix, Handler
import time


# defs
# Future plan: use database to store operating data, instead of using global variable.
op_data= {
    "temp": 5.0,
    "preci": 0.0,
    "solar": 0.0,
    "dust": 0.0,
    "flow_sup": 1800.0,
    "temp_sup": 25.0,
    "temp_room": 20.0,
    "temp_constr": 10.0,
    "temp_insul": 10.0,
    "damp_cmd": True,
    "pump_cmd": True,
    "htg_pos": 60.0,
    "htg_pwr": 14.0
}


# const
# All constants stored in TXT files


# code
ambient = Ambient()
ambient.load_config()
ambient.create_meteo_headers()
ambient.get_coordinates()

controls = Climatix()
controls.load_config()
controls.climatix_auth()
# 1st time initialization, to start from good values, not from zeros
control_values = controls.read_JSON(["damp_cmd", "pump_cmd", "htg_pos", "temp", "temp_sup", "temp_room", "temp_extr"])
for key in control_values:
    op_data[key] = control_values[key]

data_handler = Handler()
op_data = data_handler.recover_op_data(op_data)

building = Building(op_data["temp_room"], op_data["temp_constr"], op_data["temp_insul"])
building.load_config()

for hrs in range(48):
    ambient.get_dates()
    ambient.renew_forecast()
    ambient.renew_dust_measure()

    for sec in range(3600):
        print("Elapsed: {}hrs, {}sec, ".format(hrs,sec), end="")
        outside_conditions = ambient.simulate()
        for key in ["temp", "preci", "solar", "dust"]:
            op_data[key] = outside_conditions[key]

        control_values = controls.read_JSON(["damp_cmd", "pump_cmd", "htg_pos"])
        for key in control_values:
            op_data[key] = control_values[key]

        internal_conditions = building.calculate(op_data["temp"], op_data["temp_sup"], op_data["damp_cmd"])
        print(internal_conditions)
        for key in internal_conditions:
            op_data[key] = internal_conditions[key]

        model_values = controls.calculate(op_data["temp"], op_data["temp_room"], op_data["damp_cmd"], op_data["pump_cmd"], op_data["htg_pos"], op_data["htg_pwr"])
        print(model_values)
        for key in model_values:
            op_data[key] = model_values[key]

        controls.write_JSON({"temp": op_data["temp"], "temp_sup": op_data["temp_sup"], "temp_room": op_data["temp_room"], "temp_extr": op_data["temp_room"]})

        if (sec % 60) == 0:
            data_handler.store_op_data(op_data)
            data_handler.dump_to_file(op_data)
        time.sleep(0.930)
