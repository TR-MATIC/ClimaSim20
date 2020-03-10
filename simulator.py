# packages
from lib_class import Ambient, Building, Climatix
import time


# defs
# Future plan: use database to store operating data, instead of using global variable.
op_data= {
    "temp": 6.0,
    "preci": 0.0,
    "solar": 0.0,
    "dust": 0.0,
    "flow_sup": 1800.0,
    "temp_sup": 27.0,
    "temp_room": 17.0,
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

building = Building()
building.load_config()

controls = Climatix()
controls.load_config()
controls.climatix_auth()

for hrs in range(24):
    ambient.get_dates()
    ambient.renew_forecast()
    ambient.renew_dust_measure()

    for sec in range(3600):
        outside_conditions = ambient.simulate()
        for key in ["temp", "preci", "solar", "dust"]:
            op_data[key] = outside_conditions[key]

        control_values = controls.read_JSON(["damp_cmd", "pump_cmd", "htg_pos"])
        for key in control_values:
            op_data[key] = control_values[key]

        internal_conditions = building.calculate(op_data["temp"], op_data["temp_sup"])
        for key in ["temp_room", "temp_constr", "temp_insul"]:
            op_data[key] = internal_conditions[key]

        model_values = controls.calculate(op_data["temp"], op_data["temp_room"], op_data["damp_cmd"], op_data["pump_cmd"], op_data["htg_pos"], op_data["htg_pwr"])
        for key in model_values:
            op_data[key] = model_values[key]

        controls.write_JSON({"temp": op_data["temp"], "temp_sup": op_data["temp_sup"], "temp_room": op_data["temp_room"], "temp_extr": op_data["temp_room"]})

        print(op_data)

        time.sleep(1.0)
