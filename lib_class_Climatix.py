# packages
import requests
from datetime import datetime
import time


# defs
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

    def calculate(self, temp, temp_room, damp_cmd, fans_stp, flow_sup, pump_cmd, clg_cmd, htg_pos, clg_pos,
                  htg_pwr, clg_pwr, dust, dust_depo):
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
            dust_depo = dust_depo
        else:
            temp_sup = temp + (htg_pwr - clg_pwr) * 1000 / (flow_sup / 3600 * 1.2 * 1005)
            dust_depo = dust_depo + (1/100000000 * 2.2 * 3 * 4 * dust)
        if temp_sup > 80.0:
            temp_sup = 80.0
        elif temp_sup < -20.0:
            temp_sup = -20.0
        return {"flow_sup": flow_sup, "temp_sup": temp_sup, "htg_pwr": htg_pwr, "clg_pwr": clg_pwr, "dust_depo": dust_depo}
