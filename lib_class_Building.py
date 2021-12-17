# packages
# import requests
# from datetime import datetime
import time


# defs
# Simplified model, with sensible response, but without sophisticated modelling and calculations.
class Building(object):
    def __init__(self, temp_room=20.0, temp_constr=15.0, temp_insul=10.0, config_path="building_data.txt"):
        self.__config_path = config_path
        self.__config = {}
        # room_avg = 1 / List of fields available/expected in TXT configuration.
        # room_tau = 1
        # constr_avg = 2
        # constr_tau = 36
        # insul_avg = 4
        # insul_tau = 2
        # AVG - coefficient of averaging temperatures, TAU - time constant for 1st order inertia
        self.__temp_room = [temp_room, temp_room]
        self.__temp_constr = [temp_constr, temp_constr]
        self.__temp_insul = [temp_insul, temp_insul]
        self.__curr_time = time.time()
        self.__last_time = time.time()

    @property
    def config_path(self):
        return self.__config_path

    @property
    def config(self):
        return self.__config

    @config.setter
    def config(self, config: dict):
        self.__config = config

    def calculate(self, op_data: dict):
        # prepare data
        temp_rm = self.__temp_room[0]
        temp_con = self.__temp_constr[0]
        temp_ins = self.__temp_insul[0]
        avg_rm = self.__config["room_avg"]
        avg_con = self.__config["constr_avg"]
        avg_ins = self.__config["insul_avg"]
        tau_rm = self.__config["room_tau"]
        tau_con = self.__config["constr_tau"]
        tau_ins = self.__config["insul_tau"]
        # handle timing
        self.__curr_time = time.time()
        ti_diff = (self.__curr_time - self.__last_time) / 3600
        print("ti_diff : {:1.5} sec".format(self.__curr_time - self.__last_time))
        self.__last_time = self.__curr_time
        # do calculations
        if op_data["flow_su"] > 0.0:
            coeff = op_data["flow_su"]/7610.0
        else:
            coeff = 1.0
        self.__temp_room[1] = temp_rm + ((avg_rm * op_data["temp_su"] + temp_con) / (avg_rm + 1) - temp_rm) * coeff * (ti_diff / tau_rm)
        self.__temp_constr[1] = temp_con + ((avg_con * self.__temp_room[1] + temp_ins) / (avg_con + 1) - temp_con) * 1 * (ti_diff / tau_con)
        self.__temp_insul[1] = temp_ins + ((avg_ins * self.__temp_constr[1] + op_data["temp"]) / (avg_ins + 1) - temp_ins) * 1 * (ti_diff / tau_ins)
        # update storage
        self.__temp_room[0] = self.__temp_room[1]
        self.__temp_constr[0] = self.__temp_constr[1]
        self.__temp_insul[0] = self.__temp_insul[1]
        return {"temp_rm": self.__temp_room[1],
                "temp_con": self.__temp_constr[1],
                "temp_ins": self.__temp_insul[1],
                "temp_ex": self.__temp_room[1],
                "ti_diff": ti_diff}


# Static methods, supporting the extended building model.
def transfer_efficiency(delta_t: float, coeff=1.028) -> float:
    output = 1.0 - coeff ** (-1.0 * (delta_t ** 2))
    return output


# Extended model, with sophisticated modelling and calculations.
class BuildingEx(object):
    def __init__(self, config_path="buildingex_data.txt"):
        self.__config_path = config_path
        self.__config = {}
        self.__params = {}

    @property
    def config_path(self):
        return self.__config_path

    @property
    def config(self):
        return self.__config

    @config.setter
    def config(self, config: dict):
        self.__config = config

    @property
    def params(self):
        return self.__params

    @params.setter
    def params(self, params: dict):
        self.__params = params

    def initialize_params(self) -> bool:
        # These are constant parameters which characterize the building.
        # Wall area is calculated as sum of the flat roof (DxL) and all vertical walls (2xDxH+2xLxH).
        # Assumption 1: no heat exchange through the bottom.
        # Assumption 2: both roof and walls have the same structure - layer of concrete and insulation.
        wall_area = self.__config["building_D"] * self.__config["building_L"] + \
                    2 * (self.__config["building_D"] + self.__config["building_L"]) * self.__config["building_H"]
        wall_volume = wall_area * self.__config["concrete_thickness"]
        wall_mass = wall_volume * self.__config["concrete_density"]
        # This conductance is not a material constant, but it's [W/K] for entire building.
        wall_conductance = wall_area * self.__config["concrete_lambda"] / self.__config["concrete_thickness"]
        # This heatup energy is not a material constant, but it's [J/K] for entire building.
        wall_heatup_energy = wall_mass * self.__config["concrete_spec_heat"]
        # Window area is a fraction of the walls.
        window_area = self.__config["glass_ratio"] * self.__config["building_L"] * self.__config["building_H"]
        # Window specific power is parameter of entire glass surface.
        # Note: windows are not calculated separately for heat insulation/dissipation.
        window_spec_power = window_area * self.__config["glass_capture"]
        air_volume = self.__config["building_D"] * self.__config["building_L"] * self.__config["building_H"]
        air_mass = air_volume * self.__config["air_density"]
        air_conductance = wall_area * self.__config["air_lambda"] / self.config["air_thickness"]
        air_heatup_energy = air_mass * self.__config["air_spec_heat"]
        insulation_volume = wall_area * self.__config["styrofoam_thickness"]
        insulation_mass = insulation_volume * self.__config["styrofoam_density"]
        insulation_conductance = wall_area * self.__config["styrofoam_lambda"] / self.__config["styrofoam_thickness"]
        insulation_heatup_energy = insulation_mass * self.__config["styrofoam_spec_heat"]
        # These are constants stored internally in the building object
        self.__params["wall_C"] = wall_conductance
        self.__params["wall_HE"] = wall_heatup_energy
        self.__params["window_SP"] = window_spec_power
        self.__params["air_C"] = air_conductance
        self.__params["air_HE"] = air_heatup_energy
        self.__params["ins_C"] = insulation_conductance
        self.__params["ins_HE"] = insulation_heatup_energy
        return True

    def power_delivery(self, op_data: dict) -> float:
        temp_delta = op_data["temp_su"] - op_data["temp_rm"]
        power = transfer_efficiency(temp_delta) * temp_delta * \
                self.__config["air_spec_heat"] * self.__config["air_density"] * 1/3600 * op_data["flow_su"] + \
                self.__params["window_SP"] * op_data["solar"]
        return power

    def calculate_layer(self, layer_name: str, op_data: dict, power_source: float, temp_sink: float) -> dict:
        key_c = layer_name + "_C"
        key_he = layer_name + "_HE"
        key_aq = layer_name + "_AQ"
        key_pb = layer_name + "_PB"
        accumulated_energy = op_data[key_aq] + 0.0036 * op_data[key_pb] * op_data["ti_diff"]
        temp_layer = 1000000 * accumulated_energy / self.__params[key_he] - 273.15
        power_sink = (temp_layer - temp_sink) * self.__params[key_c]
        power_balance = power_source - power_sink
        return {"AQ": accumulated_energy,
                "PB": power_balance,
                "power_sink": power_sink,
                "temperature": temp_layer}

    def simulate_dioxide(self, op_data: dict) -> float:
        building_vol = self.__config["building_D"] * self.__config["building_L"] * self.__config["building_H"]
        number_of_people = int(5 + 100 * (op_data["preci"] / 50 + op_data["solar"] / 500 + op_data["dust"] / 50))
        exhale_flow = number_of_people * 1200 * 0.0005
        exhale_co2 = 40000.0
        supply_co2 = 400.0
        carbon_dioxide = ((exhale_flow * exhale_co2 + op_data["flow_su"] * supply_co2) * op_data["ti_diff"] + \
                         (building_vol - (exhale_flow + op_data["flow_su"]) * op_data["ti_diff"]) * op_data["air_q"]) / \
                         building_vol
        return carbon_dioxide
