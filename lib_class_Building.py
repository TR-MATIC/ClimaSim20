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


# Extended model, with sophisticated modelling and calculations.
class BuildingEx(object):
    def __init__(self, config_path="buildingex_data.txt"):
        self.__config_path = config_path
        self.__config = {}
        self.__params = {}
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

    @property
    def params(self):
        return self.__params

    @params.setter
    def params(self, params: dict):
        self.__params = params

    def initialize_params(self):
        wall_area = 2 * (self.__config["building_D"] + self.__config["building_L"]) * self.__config["building_H"]
        wall_volume = wall_area * self.__config["concr_thickness"]
        wall_mass = wall_volume * self.__config["concr_density"]
        wall_conductance = wall_area * self.__config["concr_lambda"] / self.__config["concr_thickness"]
        wall_heating_energy = wall_mass * self.__config["concr_spec_heat"]
        window_area = self.__config["glass_ratio"] * self.__config["building_L"] * self.__config["building_H"]
        window_spec_power = window_area * self.__config["glass_capture"]
        air_volume = self.__config["building_D"] * self.__config["building_L"] * self.__config["building_H"]
        air_mass = air_volume * self.__config["air_density"]
        air_conductance = wall_area * self.__config["air_lambda"] / self.config["air_thickness"]
        air_heating_energy = air_mass * self.__config["air_spec_heat"]
        insulation_volume = wall_area * self.__config["styro_thickness"]
        insulation_mass = insulation_volume * self.__config["styro_density"]
        insulation_conductance = wall_area * self.__config["styro_lambda"] / self.__config["styro_thickness"]
        insulation_heating_energy = insulation_mass * self.__config["styro_spec_heat"]
        return {"wall_A": wall_area,
                "wall_V": wall_volume,
                "wall_M": wall_mass,
                "wall_C": wall_conductance,
                "wall_HE": wall_heating_energy,
                "window_A": window_area,
                "window_SP": window_spec_power,
                "air_A": wall_area,
                "air_V": air_volume,
                "air_M": air_mass,
                "air_C": air_conductance,
                "air_HE": air_heating_energy,
                "insu_A": wall_area,
                "insu_V": insulation_volume,
                "insu_M": insulation_mass,
                "insu_C": insulation_conductance,
                "insu_HE": insulation_heating_energy}
