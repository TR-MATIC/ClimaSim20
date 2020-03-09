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
    def __init__(self, config_path="building_data.txt"):
        self.__config_path = config_path
        self.__config = {}
        # room_avg = 1 / List of fields available/expected in TXT configuration.
        # room_tau = 1
        # constr_avg = 2
        # constr_tau = 36
        # insul_avg = 4
        # insul_tau = 2
        # AVG - coefficient of averaging temperatures, TAU - time constant for 1st order intertia
        self.__temp_room = [0.0, 0.0]
        self.__temp_constr = [0.0, 0.0]
        self.__temp_insul = [0.0, 0.0]
        self.__curr_time = time.time()
        self.__last_time = time.time()

    def load_config(self):
        config_file = open(self.__config_path, mode="r")
        config_data = config_file.readlines()
        for line in config_data:
            marker = line.find("=")
            key = line[0:marker]
            value = line[(marker + 1):].rstrip("\n")
            self.__config.update({key: value})

    def calculate(self, temp, te_sup):
        # prepare data
        te_rm = self.__temp_room[0]
        te_con = self.__temp_constr[0]
        te_ins = self.__temp_insul[0]
        av_rm = float(self.__config["room_avg"])
        av_con = float(self.__config["constr_avg"])
        av_ins = float(self.__config["insul_avg"])
        tau_rm = float(self.__config["room_tau"])
        tau_con = float(self.__config["constr_tau"])
        tau_ins = float(self.__config["insul_tau"])
        # handle timing
        self.__curr_time = time.time()
        ti_diff = self.__curr_time - self.__last_time
        self.__last_time = self.__curr_time
        # do calculations
        self.__temp_room[1] = te_rm + ((av_rm * te_sup + te_con) / (av_rm + 1) - te_rm) * (ti_diff/tau_rm)
        self.__temp_constr[1] = te_con + ((av_con * te_rm + te_ins) / (av_con + 1) - te_con) * (ti_diff/tau_con)
        self.__temp_insul[1] = te_ins + ((av_ins * te_con + temp) / (av_ins + 1) - te_ins) * (ti_diff/tau_ins)
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
        # present_val = AAE=
        # tracking_sel = QDA=
        # tracking_com_val = QzA=
        # reliability_com = RDA=
        # TOa = AyLizxoD
        # TSu = AyJesBoD
        # TRm = AyLj7BoD
        # TEx = AyJgbhoD
        # TEh = AyK/nxoD
        # DpFiltSu = AyIQnxoD
        # DpFiltEx = AyJ8NRoD
        # FireAlm = BCJibxoD
        # FrostAlm = BCIuUxoD
        # PumpAlm = BCLnuhoD
        # HRecAlm = BCJTRhoD
        # DampCmd = ByIaGBoD
        # PumpCmd = ByIYKBoD
        # HRecCmd = ByJB6hoD
        # FanSuCmd = CCKoVRoD
        # FanExCmd = CCJ/ORoD
        # HtgPos = BiJhZhoD
        # HRecPos = BiIiFxoD
        self.__io = {}
        self.__current_time = {}
        self.__current_date = {}

    def load_config(self):
        config_file = open(self.__config_path, mode="r")
        config_data = config_file.readlines()
        for line in config_data:
            marker = line.find("=")
            key = line[0:marker]
            value = line[(marker + 1):].rstrip("\n")
            self.__config.update({key: value})

    def read_JSON(self):
        pass

    def write_JSON(self):
        pass

    def calculate(self):
        pass
