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
        self.__temperature = {}
        self.__precipitation = {}
        self.__solar_radiation = {}
        self.__dust_measure = {"times": [], "data": []}
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
        return True

    def create_meteo_headers(self):
        self.__meteo_headers.update({"Authorization": "Token {}".format(self.__config["meteo_api_key"])})
        return True

    def get_coordinates(self):
        coordinates_url = "{}/api/{}/model/{}/grid/{}/latlon2rowcol/{},{}".format(
            self.__config["meteo_url"],
            self.__config["api"],
            self.__config["model"],
            self.__config["grid"],
            self.__config["latitude"],
            self.__config["longitude"])
        try:
            coordinates = requests.get(
                coordinates_url,
                headers=self.__meteo_headers,
                timeout=1.000)
        except requests.Timeout:
            output = {"error": "get_co_tout"}
        except requests.ConnectionError:
            output = {"error": "get_co_conn"}
        except:
            output = {"error": "get_co_othr"}
        else:
            if coordinates.status_code == 200:
                output = {"error": "get_co_none"}
                row = coordinates.json()["points"][0]["row"]
                col = coordinates.json()["points"][0]["col"]
                self.__meteo_coordinates = "{},{}".format(row, col)
            else:
                output = {"error": "get_co_" + str(coordinates.status_code)}
        return output

    def get_date(self, field, level):
        dates_url = "{}/api/{}/model/{}/grid/{}/coordinates/{}/field/{}/level/{}/date/".format(
            self.__config["meteo_url"],
            self.__config["api"],
            self.__config["model"],
            self.__config["grid"],
            self.__meteo_coordinates,
            field,
            level)
        try:
            date_entries = requests.get(
                dates_url,
                headers=self.__meteo_headers,
                timeout=1.000)
        except requests.Timeout:
            output = {"error": "get_da_tout"}
        except requests.ConnectionError:
            output = {"error": "get_da_conn"}
        except:
            output = {"error": "get_da_othr"}
        else:
            if date_entries.status_code == 200:
                how_many = len(date_entries.json()["dates"])
                last_entry = date_entries.json()["dates"][how_many-1]
                starting_date = datetime.fromisoformat(last_entry["starting-date"])
                count = last_entry["count"]
                interval = last_entry["interval"]
                latest_valid_date = datetime.fromtimestamp(starting_date.timestamp() + (count - 1) * interval * 3600)
                output = latest_valid_date.strftime("%Y-%m-%dT%H")
            else:
                output = {"error": "get_da_" + str(date_entries.status_code)}
        return output

    def data_point_url(self, field, level):
        forecast_url = "{}/api/{}/model/{}/grid/{}/coordinates/{}/field/{}/level/{}/date/{}/forecast/".format(
            self.__config["meteo_url"],
            self.__config["api"],
            self.__config["model"],
            self.__config["grid"],
            self.__meteo_coordinates,
            field,
            level,
            self.get_date(field, level))
        info_url = "{}/api/{}/model/{}/grid/{}/coordinates/{}/field/{}/level/{}/date/{}/info/".format(
            self.__config["meteo_url"],
            self.__config["api"],
            self.__config["model"],
            self.__config["grid"],
            self.__meteo_coordinates,
            field,
            level,
            self.get_date(field, level))
        return {"forecast": forecast_url, "info": info_url}

    def get_forecast(self, field, level):
        try:
            response = requests.post(
                self.data_point_url(field, level)["forecast"],
                headers=self.__meteo_headers,
                timeout=1.000)
        except requests.Timeout:
            output = {"error": "get_fo_tout"}
        except requests.ConnectionError:
            output = {"error": "get_fo_conn"}
        except:
            output = {"error": "get_fo_othr"}
        else:
            if response.status_code == 200:
                output = response.json()
            else:
                output = {"error": "get_fo_" + str(response.status_code)}
        print(output)
        return output

    def renew_forecast(self):
        temperature_forecast = self.get_forecast(
            self.__config["temperature_field"],
            self.__config["temperature_level"])
        self.__temperature = temperature_forecast
        precipitation_forecast = self.get_forecast(
            self.__config["precipitation_field"],
            self.__config["precipitation_level"])
        self.__precipitation = precipitation_forecast
        solar_radiation_forecast = self.get_forecast(
            self.__config["solar_radiation_field"],
            self.__config["solar_radiation_level"])
        self.__solar_radiation = solar_radiation_forecast
        return True

    def renew_dust_measure(self):
        pm10_url = self.__config["gios_url"] + self.__config["pm10_id"]
        try:
            dust_data = requests.get(pm10_url, timeout=1.500)
        except requests.Timeout:
            output = {"error": "get_du_tout"}
        except requests.ConnectionError:
            output = {"error": "get_du_conn"}
        except:
            output = {"error": "get_du_othr"}
        else:
            if dust_data.status_code == 200:
                dust_record = dust_data.json()
                for data in dust_record["values"]:
                    if data["value"] not in ["None", None]:
                        dust_measure = float(data["value"])
                    else:
                        dust_measure = 0.0
                    self.__dust_measure["times"].append(data["date"][0:16])
                    self.__dust_measure["data"].append(dust_measure)
                output = {"error": "get_du_none"}
            else:
                output = {"error": "get_du_" + str(dust_data.status_code)}
            print(dust_record)
        return output

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
        if "times" in self.__temperature.keys():
            for index, timestamp in enumerate(self.__temperature["times"]):
                if last_timestamp in timestamp:
                    last_temp = float(self.__temperature["data"][index]) - 273.0
                    next_temp = float(self.__temperature["data"][index + 1]) - 273.0
                    break
        self.__current["temp"] = last_temp + 1/360 * elapsed_minutes * (next_temp - last_temp)
        # This part of the code calculates current precipitation
        last_preci = next_preci = 0.0
        if "times" in self.__precipitation.keys():
            for index, timestamp in enumerate(self.__precipitation["times"]):
                if last_timestamp in timestamp:
                    last_preci = float(self.__precipitation["data"][index])
                    next_preci = float(self.__precipitation["data"][index + 1])
                    break
        self.__current["preci"] = last_preci + 1/360 * elapsed_minutes * (next_preci - last_preci)
        # This part of the code calculates current solar radiation
        last_solar = next_solar = 0.0
        if "times" in self.__precipitation.keys():
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
        dust_n0 = self.__dust_measure["data"][0]
        dust_n1 = self.__dust_measure["data"][1]
        dust_n2 = self.__dust_measure["data"][2]
        dust_n3 = self.__dust_measure["data"][3]
        if dust_n0 > 0.0:
            self.__current["dust"] = dust_n0 + 1/60 * elapsed_minutes * (dust_n0 - dust_n1)
        elif dust_n1 > 0.0:
            self.__current["dust"] = dust_n1 + 1/60 * (elapsed_minutes + 60) * (dust_n1 - dust_n2)
        else:
            self.__current["dust"] = dust_n2 + 1/60 * (elapsed_minutes + 120) * (dust_n2 - dust_n3)
        return self.__current


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
            self.__temp_room[1] = temp_rm + ((avg_rm * coeff * temp_sup + temp_con) / (avg_rm * coeff + 1) - temp_rm) * (ti_diff / tau_rm)
            self.__temp_constr[1] = temp_con + ((avg_con * coeff * self.__temp_room[1] + temp_ins) / (avg_con * coeff + 1) - temp_con) * (ti_diff / tau_con)
            self.__temp_insul[1] = temp_ins + ((avg_ins * coeff * self.__temp_constr[1] + temp) / (avg_ins * coeff + 1) - temp_ins) * (ti_diff / tau_ins)
        else:
            coeff = 0.2
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
        # ClgPos =

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

    def read_json(self, ao_list):
        output = {}
        climatix_params = self.climatix_params_r(ao_list)
        try:
            climatix_get = requests.get(
                self.__config["climatix_url"],
                auth=self.climatix_auth(),
                params=climatix_params,
                timeout=0.750)
        except requests.Timeout:
            output = {"error": "get_rd_tout"}
        except requests.ConnectionError:
            output = {"error": "get_rd_conn"}
        except:
            output = {"error": "get_rd_othr"}
        else:
            if climatix_get.status_code == 200:
                received = climatix_get.json()["values"]
                for cnt, key in enumerate(received):
                    if type(received[key]) == list:
                        output.update({ao_list[cnt]: received[key][0]})
                    else:
                        output.update({ao_list[cnt]: received[key]})
            else:
                output = {"error": "get_rd_" + str(climatix_get.status_code)}
        return output

    def climatix_params_w(self, ao_dict: dict):
        climatix_params = {"fn": "write"}
        params_list = []
        for key in ao_dict:
            params_list.append(self.__config[key] + self.__config["tracking_sel"] + ";" + "1")
            params_list.append(self.__config[key] + self.__config["tracking_com_val"] + ";" + str(ao_dict[key]))
        climatix_params.update({"oa": params_list})
        climatix_params.update({"pin": self.__config["climatix_pin"]})
        return climatix_params

    def write_json(self, ao_dict: dict):
        output = {}
        try:
            climatix_get = requests.get(
                self.__config["climatix_url"],
                auth=self.climatix_auth(),
                params=self.climatix_params_w(ao_dict),
                timeout=0.750)
        except requests.Timeout:
            output = {"error": "get_wr_tout"}
        except requests.ConnectionError:
            output = {"error": "get_wr_conn"}
        except:
            output = {"error": "get_wr_othr"}
        else:
            if climatix_get.status_code == 200:
                output = climatix_get.json()
            else:
                output = {"error": "get_wr_" + str(climatix_get.status_code)}
        return output

    def calculate(self, temp, temp_room, damp_cmd, fans_stp, flow_sup, pump_cmd, clg_cmd, htg_pos, clg_pos, htg_pwr, clg_pwr):
        # calculation of heating power from the heater
        if pump_cmd:
            htg_pwr_demand = 22.0 * 1/100 * htg_pos
        else:
            htg_pwr_demand = 0.0
        if htg_pwr < (htg_pwr_demand - 1.0):
            htg_pwr = htg_pwr + 0.2
        elif htg_pwr < (htg_pwr_demand - 0.1):
            htg_pwr = htg_pwr + 0.05
        elif htg_pwr > (htg_pwr_demand + 1.0):
            htg_pwr = htg_pwr - 0.2
        elif htg_pwr > (htg_pwr_demand + 0.1):
            htg_pwr = htg_pwr - 0.05
        else:
            htg_pwr = htg_pwr_demand
        # calculation of cooling power from the cooler
        clg_pwr_demand = 20.0 * 1/100 * clg_pos
        if clg_cmd:
            if clg_pwr < (clg_pwr_demand - 1.0):
                clg_pwr = clg_pwr + 0.2
            elif clg_pwr < (clg_pwr_demand - 0.1):
                clg_pwr = clg_pwr + 0.05
            elif clg_pwr > (clg_pwr_demand + 1.0):
                clg_pwr = clg_pwr - 0.2
            elif clg_pwr > (clg_pwr_demand + 0.1):
                clg_pwr = clg_pwr - 0.05
            else:
                clg_pwr = clg_pwr
        else:
            clg_pwr = 0.0
        # calculation of fan speed and corresponding air volume flow
        # the flow demand must be calculated first, according to damper opening and fan step
        if damp_cmd:
            if fans_stp == 0:
                flow_sup_demand = 0.0
            elif fans_stp == 1:
                flow_sup_demand = 1600
            elif fans_stp == 2:
                flow_sup_demand = 2400
            else:
                flow_sup_demand = 2400
        else:
            flow_sup_demand = 0.0
        # then the air volume flow must follow the demand, but with appropriate inertia
        if flow_sup < (flow_sup_demand - 100):
            flow_sup = flow_sup + 50
        elif flow_sup <= (flow_sup_demand - 10):
            flow_sup = flow_sup + 10
        elif flow_sup > (flow_sup_demand + 100):
            flow_sup = flow_sup - 50
        elif flow_sup >= (flow_sup_demand + 10):
            flow_sup = flow_sup - 10
        else:
            flow_sup = flow_sup_demand
        # finally, from htg the supply temperature is calculated
        if flow_sup == 0.0:
            temp_sup = temp_room
        else:
            temp_sup = temp + (htg_pwr - clg_pwr) * 1000 / (flow_sup / 3600 * 1.2 * 1005)
        if temp_sup > 80.0:
            temp_sup = 80.0
        elif temp_sup < -20.0:
            temp_sup = -20.0
        return {"flow_sup": flow_sup, "temp_sup": temp_sup, "htg_pwr": htg_pwr, "clg_pwr": clg_pwr}


class Handler(object):
    def __init__(self, op_data_path="op_data.txt", dump_file_name="dump"):
        self.__op_data_path = op_data_path
        self.__timestamp = time.strftime("_%y%m%d_%H%M")
        self.__dump_file_path = dump_file_name + self.__timestamp + ".txt"
        self.__script_started = time.time()
        self.__total_sec = 0
        self.__store_sec = 0

    def timer(self, step=2):
        trig = False
        self.__total_sec = int(time.time() - self.__script_started)
        if self.__total_sec > self.__store_sec:
            trig = (self.__total_sec % step == 0)
        if trig:
            self.__store_sec = self.__total_sec
        elapsed_sec = self.__total_sec % 3600
        elapsed_hrs = self.__total_sec // 3600
        return trig, elapsed_hrs, elapsed_sec

    def recover_op_data(self, op_data: dict):
        new_file = False
        try:
            op_data_file = open(self.__op_data_path, mode="r")
        except FileNotFoundError:
            op_data_file = open(self.__op_data_path, mode="w")
            new_file = True
        if not new_file:
            file_content = op_data_file.readlines()
            op_data_file.close()
            for line in file_content:
                marker = line.find("=")
                key = line[0:marker]
                value = line[(marker + 1):].rstrip("\n")
                if key == "error":
                    pass
                elif value == "True":
                    op_data.update({key: True})
                elif value == "False":
                    op_data.update({key: False})
                else:
                    op_data.update({key: float(value)})
        else:
            for key in op_data:
                line = "{}={}\n".format(key, op_data[key])
                op_data_file.writelines(line)
            op_data_file.close()
        return op_data

    def store_op_data(self, op_data: dict):
        op_data_file = open(self.__op_data_path, mode="w")
        for key in op_data:
            line = "{}={}\n".format(key, op_data[key])
            op_data_file.writelines(line)
        op_data_file.close()
        return True

    def dump_to_file(self, op_data: dict):
        report_file = open(self.__dump_file_path, mode="a")
        line = "{} ; ".format(time.strftime("%H:%M"))
        for key in op_data:
            if op_data[key] in (True, False):
                line = line + "{}={}; ".format(key, op_data[key])
            elif key in ("error"):
                line = line + "{}={}; ".format(key, op_data[key])
            else:
                line = line + "{}={:.3f}; ".format(key, op_data[key])
        line = line + "\n"
        report_file.writelines(line)
        report_file.close()
        return True
