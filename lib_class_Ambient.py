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
        self.__meteo_date = ""
        self.__temperature = {}
        self.__precipitation = {}
        self.__solar_radiation = {}
        self.__dust_measure = {}
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
            status = {"error": "get_coor_tout"}
        except requests.ConnectionError:
            status = {"error": "get_coor_conn"}
        except:
            status = {"error": "get_coor_othr"}
        else:
            if coordinates.status_code == 200:
                row = coordinates.json()["points"][0]["row"]
                col = coordinates.json()["points"][0]["col"]
                self.__meteo_coordinates = "{},{}".format(row, col)
                status = {"error": "NONE"}
            else:
                status = {"error": "get_coor_" + str(coordinates.status_code)}
        return status

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
            status = {"error": "get_date_tout"}
        except requests.ConnectionError:
            status = {"error": "get_date_conn"}
        except:
            status = {"error": "get_date_othr"}
        else:
            if date_entries.status_code == 200:
                how_many = len(date_entries.json()["dates"])
                last_entry = date_entries.json()["dates"][how_many-1]
                starting_date = datetime.fromisoformat(last_entry["starting-date"])
                count = last_entry["count"]
                interval = last_entry["interval"]
                latest_valid_date = datetime.fromtimestamp(starting_date.timestamp() + (count - 1) * interval * 3600)
                self.__meteo_date = latest_valid_date.strftime("%Y-%m-%dT%H")
                status = {"error": "NONE"}
            else:
                status = {"error": "get_date_" + str(date_entries.status_code)}
        return status

    def data_point_url(self, field, level):
        self.get_date(field, level)
        forecast_url = "{}/api/{}/model/{}/grid/{}/coordinates/{}/field/{}/level/{}/date/{}/forecast/".format(
            self.__config["meteo_url"],
            self.__config["api"],
            self.__config["model"],
            self.__config["grid"],
            self.__meteo_coordinates,
            field,
            level,
            self.__meteo_date)
        info_url = "{}/api/{}/model/{}/grid/{}/coordinates/{}/field/{}/level/{}/date/{}/info/".format(
            self.__config["meteo_url"],
            self.__config["api"],
            self.__config["model"],
            self.__config["grid"],
            self.__meteo_coordinates,
            field,
            level,
            self.__meteo_date)
        return {"forecast": forecast_url, "info": info_url}

    def get_forecast(self, field, level):
        output = {}
        #output = {'times': [], 'data': []}
        try:
            response = requests.post(
                self.data_point_url(field, level)["forecast"],
                headers=self.__meteo_headers,
                timeout=1.000)
        except requests.Timeout:
            status = {"error": "get_fcst_tout"}
        except requests.ConnectionError:
            status = {"error": "get_fcst_conn"}
        except:
            status = {"error": "get_fcst_othr"}
        else:
            if response.status_code == 200:
                output = response.json()
                status = {"error": "NONE"}
            else:
                status = {"error": "get_fcst_" + str(response.status_code)}
        print("{} ; {}".format(status, output))
        return output, status

    def renew_forecast(self):
        temperature_forecast, status = self.get_forecast(
            self.__config["temperature_field"],
            self.__config["temperature_level"])
        if status["error"] == "NONE":
            self.__temperature = temperature_forecast
        precipitation_forecast, status = self.get_forecast(
            self.__config["precipitation_field"],
            self.__config["precipitation_level"])
        if status["error"] == "NONE":
            self.__precipitation = precipitation_forecast
        solar_radiation_forecast, status = self.get_forecast(
            self.__config["solar_radiation_field"],
            self.__config["solar_radiation_level"])
        if status["error"] == "NONE":
            self.__solar_radiation = solar_radiation_forecast
        return True

    def renew_dust_measure(self):
        pm10_url = self.__config["gios_url"] + self.__config["pm10_id"]
        try:
            dust_data = requests.get(pm10_url, timeout=1.500)
        except requests.Timeout:
            status = {"error": "get_du_tout"}
        except requests.ConnectionError:
            status = {"error": "get_du_conn"}
        except:
            status = {"error": "get_du_othr"}
        else:
            if dust_data.status_code == 200:
                self.__dust_measure = {"times": [], "data": []}
                dust_record = dust_data.json()
                for data in dust_record["values"]:
                    if data["value"] not in ["None", None]:
                        dust_measure = float(data["value"])
                    else:
                        dust_measure = 0.0
                    self.__dust_measure["times"].append(data["date"][0:16])
                    self.__dust_measure["data"].append(dust_measure)
                status = {"error": "NONE"}
            else:
                status = {"error": "get_du_" + str(dust_data.status_code)}
        print("{} ; {}".format(status, self.__dust_measure))
        return status

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
        if "times" in self.__dust_measure.keys():
            dust_n0 = self.__dust_measure["data"][0]
            dust_n1 = self.__dust_measure["data"][1]
            dust_n2 = self.__dust_measure["data"][2]
            dust_n3 = self.__dust_measure["data"][3]
            if dust_n0 > 0.0:
                self.__current["dust"] = 1/4 * (dust_n0 + dust_n1 + dust_n2 + dust_n3)
            elif dust_n1 > 0.0:
                self.__current["dust"] = 1/3 * (dust_n1 + dust_n2 + dust_n3)
            elif dust_n2 > 0.0:
                self.__current["dust"] = 1/2 * (dust_n2 + dust_n3)
            elif dust_n3 > 0.0:
                self.__current["dust"] = 1/1 * (dust_n3)
        else:
            self.__current["dust"] = 0.0
        return self.__current
