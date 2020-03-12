# packages
import requests
from datetime import datetime
import time


# defs
class Ambient(object):
    def __init__(self, config_path="ambient_apis.txt"):
        self.__config_path = config_path
        self.__config = {}
        # meteo_url  / List of fields available/expected in TXT configuration.
        # api
        # model
        # grid
        # latitude
        # longitude
        # meteo_api_key
        # temperature_field
        # temperature_level
        # precipitation_field
        # precipitation_level
        # solar_radiation_field
        # solar_radiation_level
        # gios_url
        # location_id
        # pm10_id
        self.__meteo_headers = {}
        self.__meteo_coordinates = ""
        self.__meteo_dates = ["", "", "", ""]
        self.__temperature = {}
        self.__precipitation = {}
        self.__solar_radiation = {}
        self.__dust_measure = {"times":[], "data":[]}
        self.__current = {"temp": 0.0, "preci": 0.0, "solar": 0.0, "dust": 0.0}

    def load_config(self):
        config_file = open(self.__config_path, mode="r")
        config_data = config_file.readlines()
        config_file.close()
        for line in config_data:
            marker = line.find("=")
            key = line[0:marker]
            value = line[(marker + 1):].rstrip("\n")
            self.__config.update({key: value})

    def create_meteo_headers(self):
        self.__meteo_headers.update({"Authorization": "Token {}".format(self.__config["meteo_api_key"])})

    def get_coordinates(self):
        coordinates_url = "{}/api/{}/model/{}/grid/{}/latlon2rowcol/{},{}".format\
            (self.__config["meteo_url"],
             self.__config["api"],
             self.__config["model"],
             self.__config["grid"],
             self.__config["latitude"],
             self.__config["longitude"])
        coordinates = requests.get(coordinates_url, headers=self.__meteo_headers)
        row = coordinates.json()["points"][0]["row"]
        col = coordinates.json()["points"][0]["col"]
        self.__meteo_coordinates = "{},{}".format(row, col)

    def get_dates(self):
        for cnt in range(4):
            time_stamp = time.time() - (cnt + 1) * 6 * 3600
            stamp_hour = datetime.fromtimestamp(time_stamp).hour
            if stamp_hour < 6:
                hour = "00"
            elif stamp_hour < 12:
                hour = "06"
            elif stamp_hour < 18:
                hour = "12"
            else:
                hour = "18"
            meteo_date = datetime.fromtimestamp(time_stamp).strftime("%Y-%m-%d")
            meteo_hour = hour
            self.__meteo_dates[cnt] = "{}T{}".format(meteo_date, meteo_hour)
        return True

    def data_point_url(self, field, level, meteo_date):
        forecast_url = "{}/api/{}/model/{}/grid/{}/coordinates/{}/field/{}/level/{}/date/{}/forecast/".format\
            (self.__config["meteo_url"],
             self.__config["api"],
             self.__config["model"],
             self.__config["grid"],
             self.__meteo_coordinates,
             field,
             level,
             meteo_date)
        info_url = "{}/api/{}/model/{}/grid/{}/coordinates/{}/field/{}/level/{}/date/{}/info/".format\
            (self.__config["meteo_url"],
             self.__config["api"],
             self.__config["model"],
             self.__config["grid"],
             self.__meteo_coordinates,
             field,
             level,
             meteo_date)
        return {"forecast": forecast_url, "info": info_url}

    def get_forecast(self, field, level, meteo_date):
        response = requests.post(self.data_point_url(field, level, meteo_date)["forecast"], headers=self.__meteo_headers)
        return response.json()

    def renew_forecast(self):
        for meteo_date in self.__meteo_dates:
            temperature_forecast = self.get_forecast\
                (self.__config["temperature_field"], self.__config["temperature_level"], meteo_date)
            if "no forecast" not in str(temperature_forecast):
                break
        self.__temperature = temperature_forecast
        for meteo_date in self.__meteo_dates:
            precipitation_forecast = self.get_forecast\
                (self.__config["precipitation_field"], self.__config["precipitation_level"], meteo_date)
            if "no forecast" not in str(precipitation_forecast):
                break
        self.__precipitation = precipitation_forecast
        for meteo_date in self.__meteo_dates:
            solar_radiation_forecast = self.get_forecast\
                (self.__config["solar_radiation_field"], self.__config["solar_radiation_level"], meteo_date)
            if "no forecast" not in str(solar_radiation_forecast):
                break
        self.__solar_radiation = solar_radiation_forecast
        return True

    def renew_dust_measure(self):
        pm10_url = self.__config["gios_url"] + self.__config["pm10_id"]
        dust_record = requests.get(pm10_url).json()
        for data in dust_record["values"]:
            if data["value"] not in ["None", None]:
                dust_measure = float(data["value"])
            else:
                dust_measure = 0.0
            self.__dust_measure["times"].append(data["date"][0:16])
            self.__dust_measure["data"].append(dust_measure)
        return True

    def simulate(self):
        current_date = time.strftime("%Y-%m-%d")
        current_hour = time.strftime("%H")
        current_min = time.strftime("%M")
        # Data from meteo API is sliced in 6-hours slots, thus the data must be taken fom 00, 06, 12, 18 hour entries
        if int(current_hour) < 6:
            last_hour = "00"
        elif int(current_hour) < 12:
            last_hour = "06"
        elif int(current_hour) < 18:
            last_hour = "12"
        else:
            last_hour = "18"
        last_timestamp = "{}T{}:00".format(current_date, last_hour)
        elapsed_minutes = (int(current_hour) % 6) * 60 + int(current_min)
        # To calculate current temperature, interpolation must be done based on the values from surrounding API readings
        # between the moment defined by last_timestamp and the one after
        # elapsed_minutes define how much time have passed from the last_timestamp
        last_temp = next_temp = 0.0
        for index, timestamp in enumerate(self.__temperature["times"]):
            if last_timestamp in timestamp:
                last_temp = float(self.__temperature["data"][index]) - 273.0
                next_temp = float(self.__temperature["data"][index + 1]) - 273.0
                break
        self.__current["temp"] = last_temp + 1/360 * elapsed_minutes * (next_temp - last_temp)
        # This part of the code calculates current precipitation
        last_preci = next_preci = 0.0
        for index, timestamp in enumerate(self.__precipitation["times"]):
            if last_timestamp in timestamp:
                last_preci = float(self.__precipitation["data"][index])
                next_preci = float(self.__precipitation["data"][index + 1])
                break
        self.__current["preci"] = last_preci + 1/360 * elapsed_minutes * (next_preci - last_preci)
        # This part of the code calculates current solar radiation
        last_solar = next_solar = 0.0
        for index, timestamp in enumerate(self.__solar_radiation["times"]):
            if last_timestamp in timestamp:
                last_solar = float(self.__solar_radiation["data"][index])
                next_solar = float(self.__solar_radiation["data"][index + 1])
                break
        self.__current["solar"] = last_solar + 1/360 * elapsed_minutes * (next_solar - last_solar)
        # Current PM10 dust concentration must be calculated as well, but the data comes from another API
        # This API responds with historical data, not simulated future values. Moreover, data for current hour
        # can be delayed for a quarter or so - and in this case API responds with 0.0 dust concentration ;)
        # And finally, this data is prepared in 1-hour slices - not in 6-hour slices. Funny, isn't it? ;)
        # Extrapolation algorithm must be smart enough to handle that.
        elapsed_minutes = int(current_min)
        dust_N0 = self.__dust_measure["data"][0]
        dust_N1 = self.__dust_measure["data"][1]
        dust_N2 = self.__dust_measure["data"][2]
        dust_N3 = self.__dust_measure["data"][3]
        if dust_N0 > 0.0:
            self.__current["dust"] = dust_N0 + 1/60 * elapsed_minutes * (dust_N0 - dust_N1)
        elif dust_N1 > 0.0:
            self.__current["dust"] = dust_N1 + 1/60 * elapsed_minutes * (dust_N1 - dust_N2)
        else:
            self.__current["dust"] = dust_N2 + 1/60 * elapsed_minutes * (dust_N2 - dust_N3)
        return self.__current


# Simplified model, with sensible response, but without sophisticated modelling and calculations.
class Building(object):
    def __init__(self, temp_room=15.0, config_path="building_data.txt"):
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
        self.__temp_constr = [12.0, 12.0]
        self.__temp_insul = [10.0, 10.0]
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

    def calculate(self, temp, temp_sup, damp_cmd):
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
        self.__last_time = self.__curr_time
        # do calculations
        if damp_cmd:
            coeff = 1.0
            self.__temp_room[1] = temp_rm + ((avg_rm * coeff * temp_sup + temp_con) / (avg_rm * coeff + 1) - temp_rm) * (ti_diff / tau_rm)
            self.__temp_constr[1] = temp_con + ((avg_con * coeff * self.__temp_room[1] + temp_ins) / (avg_con * coeff + 1) - temp_con) * (ti_diff/tau_con)
            self.__temp_insul[1] = temp_ins + ((avg_ins * coeff * self.__temp_constr[1] + temp) / (avg_ins * coeff + 1) - temp_ins) * (ti_diff/tau_ins)
        else:
            coeff = 0.3
            self.__temp_room[1] = temp_rm + ((avg_rm * coeff * temp_sup + temp_con) / (avg_rm * coeff + 1) - temp_rm) * (ti_diff / tau_rm)
            self.__temp_constr[1] = temp_con + ((avg_con * coeff * self.__temp_room[1] + temp_ins) / (avg_con * coeff + 1) - temp_con) * (ti_diff/tau_con)
            self.__temp_insul[1] = temp_ins + ((avg_ins * coeff * self.__temp_constr[1] + temp) / (avg_ins * coeff + 1) - temp_ins) * (ti_diff/tau_ins)
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


class Climatix(object):
    def __init__(self, config_path="climatix_data.txt"):
        self.__config_path = config_path
        self.__config = {}
        # climatix_url / List of fields available/expected in TXT configuration.
        # climatix_name
        # climatix_pass
        # climatix_pin
        # present_val = AAE =
        # tracking_sel = QDA =
        # tracking_com_val = QzA =
        # reliability_com = RDA =
        # TOa = AyLizxoD
        # TSu = AyJesBoD
        # TRm = AyLj7BoD
        # TEx = AyJgbhoD
        # ApiAi1 = ACPNxBoD
        # ApiAi2 = ACOu9BoD
        # ApiAi3 = ACOP5BoD
        # FrostAlm = BCIuUxoD
        # DampCmd = ByIaGBoD
        # PumpCmd = ByIYKBoD
        # FanSuCmd = CCKoVRoD
        # FanExCmd = CCJ / ORoD
        # HtgPos = BiJhZhoD

    def load_config(self):
        config_file = open(self.__config_path, mode="r")
        config_data = config_file.readlines()
        config_file.close()
        for line in config_data:
            marker = line.find("=")
            key = line[0:marker]
            value = line[(marker + 1):].rstrip("\n")
            self.__config.update({key: value})

    def climatix_auth(self):
        climatix_auth = (self.__config["climatix_name"], self.__config["climatix_pass"])
        return climatix_auth

    def climatix_params_r(self, ao_list):
        climatix_params = {"fn": "read"}
        params_list = []
        for key in ao_list:
            params_list.append(self.__config[key] + self.__config["present_val"])
        climatix_params.update({"oa": params_list})
        climatix_params.update({"pin": self.__config["climatix_pin"]})
        return climatix_params

    def read_JSON(self, ao_list):
        response = {}
        climatix_params = self.climatix_params_r(ao_list)
        try:
            climatix_get = requests.get(
                self.__config["climatix_url"],
                auth=self.climatix_auth(),
                params=climatix_params,
                timeout=0.500)
        except:
            pass
        else:
            received = climatix_get.json()["values"]
            for cnt, key in enumerate(received):
                if type(received[key]) == list:
                    response.update({ao_list[cnt]: received[key][0]})
                else:
                    response.update({ao_list[cnt]: received[key]})
        return response

    def climatix_params_w(self, ao_dict):
        climatix_params = {"fn": "write"}
        params_list = []
        for key in ao_dict:
            params_list.append(self.__config[key] + self.__config["tracking_sel"] + ";" + "1")
            params_list.append(self.__config[key] + self.__config["tracking_com_val"] + ";" + str(ao_dict[key]))
        climatix_params.update({"oa": params_list})
        climatix_params.update({"pin": self.__config["climatix_pin"]})
        return climatix_params

    def write_JSON(self, ao_dict):
        response = {}
        try:
            climatix_get = requests.get(
                self.__config["climatix_url"],
                auth=self.climatix_auth(),
                params=self.climatix_params_w(ao_dict)
            )
        except:
            pass
        else:
            response = climatix_get.json()
        return response

    def calculate(self, temp, temp_room, damp_cmd, pump_cmd, htg_pos, htg_pwr):
        htg_pwr_demand = 22.0 * 1/100 * htg_pos
        if pump_cmd:
            if htg_pwr < (htg_pwr_demand - 1.0):
                htg_pwr = htg_pwr + 0.2
            elif htg_pwr < (htg_pwr_demand - 0.1):
                htg_pwr = htg_pwr + 0.05
            elif htg_pwr > (htg_pwr_demand + 1.0):
                htg_pwr = htg_pwr - 0.2
            elif htg_pwr > (htg_pwr_demand + 0.1):
                htg_pwr = htg_pwr - 0.05
            else:
                htg_pwr = htg_pwr
        else:
            htg_pwr = 0.0
        if damp_cmd:
            flow_sup = 1800
            temp_sup = temp + htg_pwr * 1000 / ( flow_sup / 3600 * 1.2 * 1005 )
        else:
            flow_sup = 0.0
            temp_sup = temp_room
        return {"flow_sup": flow_sup, "temp_sup": temp_sup, "htg_pwr": htg_pwr}
