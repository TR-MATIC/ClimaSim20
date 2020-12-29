# packages
import requests
from datetime import datetime
import time


# defs
# Simplified model, with sensible response, but without sophisticated modelling and calculations.
class Building(object):
    def __init__(self, temp_room=15.0, temp_constr=12.0, temp_insul=10.0, config_path="building_data.txt"):
        self.__config_path = config_path
        self.__config = {}
        # room_avg = 1 / List of fields available/expected in TXT configuration.
        # room_tau = 1
        # constr_avg = 2
        # constr_tau = 36
        # insul_avg = 4
        # insul_tau = 2
        # AVG - coefficient of averaging temperatures, TAU - time constant for 1st order intertia
        self.__temp_room = [temp_room, temp_room]
        self.__temp_constr = [temp_constr, temp_constr]
        self.__temp_insul = [temp_insul, temp_insul]
        self.__curr_time = time.time()
        self.__last_time = time.time()

    def load_config(self):
        config_file = open(self.__config_path, mode="r")
        config_data = config_file.readlines()
        config_file.close()
        for line in config_data:
            marker = line.find("=")
            key = line[0:marker]
            value = line[(marker + 1):].rstrip("\n")
            self.__config.update({key: value})
        return True

    def calculate(self, temp, temp_sup, flow_sup):
        # prepare data
        temp_rm = self.__temp_room[0]
        temp_con = self.__temp_constr[0]
        temp_ins = self.__temp_insul[0]
        avg_rm = float(self.__config["room_avg"])
        avg_con = float(self.__config["constr_avg"])
        avg_ins = float(self.__config["insul_avg"])
        tau_rm = float(self.__config["room_tau"])
        tau_con = float(self.__config["constr_tau"])
        tau_ins = float(self.__config["insul_tau"])
        # handle timing
        self.__curr_time = time.time()
        ti_diff = (self.__curr_time - self.__last_time) / 3600
        print("ti_diff : {:1.5}".format(self.__curr_time - self.__last_time))
        self.__last_time = self.__curr_time
        # do calculations
        if flow_sup > 0.0:
            coeff = flow_sup/2400.0
            self.__temp_room[1] = temp_rm + ((avg_rm * temp_sup + temp_con) / (avg_rm + 1) - temp_rm) * coeff * (ti_diff / tau_rm)
            self.__temp_constr[1] = temp_con + ((avg_con * self.__temp_room[1] + temp_ins) / (avg_con + 1) - temp_con) * coeff * (ti_diff / tau_con)
            self.__temp_insul[1] = temp_ins + ((avg_ins * self.__temp_constr[1] + temp) / (avg_ins + 1) - temp_ins) * coeff * (ti_diff / tau_ins)
        else:
            coeff = 0.2
            self.__temp_room[1] = temp_rm + ((avg_rm * temp_sup + temp_con) / (avg_rm + 1) - temp_rm) * coeff * (ti_diff / tau_rm)
            self.__temp_constr[1] = temp_con + ((avg_con * self.__temp_room[1] + temp_ins) / (avg_con + 1) - temp_con) * coeff * (ti_diff/tau_con)
            self.__temp_insul[1] = temp_ins + ((avg_ins * self.__temp_constr[1] + temp) / (avg_ins + 1) - temp_ins) * coeff * (ti_diff/tau_ins)
        # update storage
        self.__temp_room[0] = self.__temp_room[1]
        self.__temp_constr[0] = self.__temp_constr[1]
        self.__temp_insul[0] = self.__temp_insul[1]
        return {
            "temp_room": self.__temp_room[1],
            "temp_constr": self.__temp_constr[1],
            "temp_insul": self.__temp_insul[1]
        }


# Extended model, with sophisticated modelling and calculations.
class BuildingEx(object):
    def __init__(self, config_path="buildingex_data.txt"):
        self.__config_path = config_path
        self.__config = {}
