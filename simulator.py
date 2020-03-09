# packages
from lib_class import Ambient, Building, Climatix
import time

# defs
# Future plan: use database to store operating data, instead of using global variable.
op_data= {
    "temp": 0.0,
    "preci": 0.0,
    "solar": 0.0,
    "dust": 0.0,
    "flow_sup": 0.0,
    "temp_sup": 0.0,
    "temp_room": 0.0,
    "temp_constr": 0.0,
    "temp_insul": 0.0,
    "damp_cmd": False,
    "pump_cmd": False,
    "htg_pos": 0.0,
    "htg_pwr": 0.0
}

# const
# All constants stored in TXT files


# climatic_auth = (climatix_name, climatix_pass)
# climatix_params_write = {"fn": "write"}
# climatix_params_read = {"fn": "read"}


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

ambient.get_dates()
ambient.renew_forecast()
ambient.renew_dust_measure()

outside_conditions = ambient.simulate()
for key in ["temp", "preci", "solar", "dust"]:
    op_data[key] = outside_conditions[key]

internal_conditions = building.calculate(op_data["temp"], op_data["temp_sup"])
for key in ["temp_room", "temp_constr", "temp_insul"]:
    op_data[key] = internal_conditions[key]

control_values = controls.read_JSON(["damp_cmd", "pump_cmd", "htg_pos"])
for key in control_values:
    op_data[key] = control_values[key]

model_values = controls.calculate(op_data["temp"], op_data["temp_room"], op_data["damp_cmd"], op_data["pump_cmd"], op_data["htg_pos"])
for key in model_values:
    op_data[key] = model_values[key]

print(op_data)

print(controls.write_JSON({"TOa": op_data["temp"], "TSu": op_data["temp_sup"], "TRm": op_data["temp_room"], "TEx": op_data["temp_room"]}))
