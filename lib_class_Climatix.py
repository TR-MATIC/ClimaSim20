# packages
import requests
# from datetime import datetime
# import time


# defs
def follow_demand(demand: float, value: float, step=1.0) -> float:
    if value < (demand - step):
        value = value + step / 2
    elif value < (demand - step / 10):
        value = value + step / 20
    elif value > (demand + step):
        value = value - step / 2
    elif value > (demand + step / 10):
        value = value - step / 20
    else:
        value = demand
    return value


class Climatix(object):
    def __init__(self, config_path="climatix_data.txt"):
        self.__config_path = config_path
        self.__config = {}
        # This is the list of key:value pairs, that should be provided for correct operation of the script.
        # The source is a TXT configuration file, by default named climatix_data.txt
        # The names on the left are required exactly like given here. They will be used as dictionary keys and are
        # referenced in the other parts of the code.
        #
        # climatix_url=http://.../jsongen.html   Note, this script uses JSONGEN interface.
        # climatix_name=.....   Siemens login...
        # climatix_pass=........!   and Siemens password, both are top-secret, you should already know it very well ;)
        # climatix_pin=####   Four digit PIN, as for Siemens HMI device.
        # present_val=AAE=   These are the "suffixes" of the BASE64 references, for example ________AAE=.
        # tracking_sel=QDA=
        # tracking_com_val=QzA=
        # reliability_com=RDA=
        # temp=AyLizxoD   These are the "bodies" of the BASE64 references, for example AyLizxoD____.
        # temp_su=AyJesBoD   They are combined together for sending appropriate control bits or tracking values
        # temp_rm=AyLj7BoD   or for the purpose of reading out the signals from the Climatix
        # temp_ex=AyJgbhoD
        # damp_cmd=ByIaGBoD
        # pump_cmd=ByIYKBoD
        # clg_cmd=ByIkKBoD
        # fan_su_cmd=CCKoVRoD
        # fan_ex_cmd=CCJ/ORoD
        # htg_pos=BiJhZhoD
        # clg_pos=BiLNeBoD
        # filt_su_pres=AyIQnxoD
        # filt_ex_pres=AyJ8NRoD

    @property
    def config_path(self):
        return self.__config_path

    @property
    def config(self):
        return self.__config

    @config.setter
    def config(self, config: dict):
        self.__config = config

    def climatix_auth(self):
        climatix_auth = (self.__config["climatix_name"], self.__config["climatix_pass"])
        return climatix_auth

    # This function prepares the content of request to JSONGEN interface.
    def climatix_params_r(self, ao_list: list) -> dict:   # The input must be a list of keys from __config dictionary.
        climatix_params = {"fn": "read"}   # Uses READ function.
        params_list = []
        for key in ao_list:
            params_list.append(self.__config[key] + self.__config["present_val"])
        climatix_params.update({"oa": params_list})
        climatix_params.update({"pin": self.__config["climatix_pin"]})
        return climatix_params

    # This function performs the actual reading request to JSONGEN interface.
    def read_json(self, ao_list: list) -> dict:   # The input ao_list is passed directly to...
        output = {}
        climatix_params = self.climatix_params_r(ao_list)   # the function, which prepares the content of the request.
        try:
            climatix_get = requests.get(
                self.__config["climatix_url"],
                auth=self.climatix_auth(),
                params=climatix_params,
                timeout=0.750)   # This is ordinary GET request. Usually Climatix responds quickly, but check timeouts.
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
        return output   # When output is bad, it contains "error" key. This is recognized by other parts of the code
                        # and the faulty data is ignored. Script can carry old, good values and stay alive for some
                        # period of time. At least is't not crashing at single wrong response of the controller.

    # This function prepares the content of request to JSONGEN interface.
    def climatix_params_w(self, ao_dict: dict) -> dict:   # The input must be a dict with keys from __config dictionary.
        climatix_params = {"fn": "write"}   # Uses WRITE function.
        params_list = []
        for key in ao_dict:
            if ao_dict[key][1]:
                params_list.append(self.__config[key] + self.__config["present_val"] + ";" + str(ao_dict[key][0]))
            else:
                params_list.append(self.__config[key] + self.__config["tracking_sel"] + ";" + "1")
                params_list.append(self.__config[key] + self.__config["tracking_com_val"] + ";" + str(ao_dict[key][0]))
        climatix_params.update({"oa": params_list})
        climatix_params.update({"pin": self.__config["climatix_pin"]})
        return climatix_params

    # This function performs the actual writing request to JSONGEN interface.
    def write_json(self, ao_dict: dict) -> dict:   # The input ao_dict is passed directly to...
        try:
            climatix_get = requests.get(
                self.__config["climatix_url"],
                auth=self.climatix_auth(),
                params=self.climatix_params_w(ao_dict),   # the function, which prepares the content of the request.
                timeout=0.750)   # This is ordinary GET request. Usually Climatix responds quickly, but check timeouts.
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
        # When output is bad, it contains "error" key. This is recognized by other parts of the code and the faulty
        # data is ignored. Script can carry old, good values and stay alive for some period of time. At least is't not
        # crashing at single wrong response of the controller.

    def calculate(self, op_data: dict) -> dict:
        # CALCULATION OF FAN SPEED AND AIR VOLUME
        # Fan flow should be delivered when (1) dampers are opened or (2) fan step is received or (3) fan analog output
        # is activated. All those are managed when available.
        global flow_sup_demand, hrec_pwr_demand
        if "damp_cmd" in op_data.keys():
            if op_data["damp_cmd"]:
                if "fan_su_pos" in op_data.keys():
                    flow_sup_demand = self.__config["ahu_vol"] * 1/100 * op_data["fan_su_pos"]
                elif "fan_su_cmd" in op_data.keys():
                    if op_data["fan_su_cmd"] == 0:
                        flow_sup_demand = 0.0
                    elif op_data["fan_su_cmd"] == 1:
                        flow_sup_demand = self.__config["ahu_vol"] * 2/3
                    elif op_data["fan_su_cmd"] == 2:
                        flow_sup_demand = self.__config["ahu_vol"] * 3/3
                else:
                    flow_sup_demand = self.__config["ahu_vol"]
            else:
                flow_sup_demand = 0.0
        else:
            if "fan_su_pos" in op_data.keys():
                flow_sup_demand = self.__config["ahu_vol"] * 1/100 * op_data["fan_su_pos"]
            elif "fan_su_cmd" in op_data.keys():
                if op_data["fan_su_cmd"] == 0:
                    flow_sup_demand = 0.0
                elif op_data["fan_su_cmd"] == 1:
                    flow_sup_demand = self.__config["ahu_vol"] * 2/3
                elif op_data["fan_su_cmd"] == 2:
                    flow_sup_demand = self.__config["ahu_vol"] * 3/3
            else:
                flow_sup_demand = 0.0
        # Well, actually we just calculated, what the flow_sup SHOULD BE but we don't apply that directly to air flow
        # calculation. This would generate jumps and oscillations between this simulation script and controller's res-
        # ponse. To solve this problem, this demand is gradually applied to volumetric flow parameter - it's simulation
        # of fan's inertia without complex mechanics and fluid modelling.
        flow_su = follow_demand(flow_sup_demand, op_data["flow_su"], 100.0)
        flow_ex = flow_su

        # CALCULATION OF HEATING POWER
        # Heating power should be delivered when (1) the heater is available, (2) the valve is open (mandatory)
        # and (3) the pump is running (optional).
        if "htg_pos" in op_data.keys():
            if "pump_cmd" in op_data.keys():
                if op_data["pump_cmd"]:
                    htg_pwr_demand = self.__config["ahu_htg"] * 1/100 * op_data["htg_pos"]
                else:
                    htg_pwr_demand = 0.0
            else:
                htg_pwr_demand = self.__config["ahu_htg"] * 1/100 * op_data["htg_pos"]
        else:
            htg_pwr_demand = 0.0
        # Then the heating power must follow the demand, but with appropriate inertia as previously.
        htg_pwr = follow_demand(htg_pwr_demand, op_data["htg_pwr"])

        # CALCULATION OF COOLING POWER
        # Cooling power should be delivered when (1) the cooler is available, (2) the valve is open (mandatory)
        # and (3) the pump is running (optional).
        if "clg_pos" in op_data.keys():
            if "clg_cmd" in op_data.keys():
                if op_data["clg_cmd"]:
                    clg_pwr_demand = self.__config["ahu_clg"] * 1/100 * op_data["clg_pos"]
                else:
                    clg_pwr_demand = 0.0
            else:
                clg_pwr_demand = self.__config["ahu_clg"] * 1/100 * op_data["clg_pos"]
        else:
            clg_pwr_demand = 0.0
        # As previously, the cooling demand is gradually applied to cooling power output.
        clg_pwr = follow_demand(clg_pwr_demand, op_data["clg_pwr"])

        # CALCULATION OF HEAT RECOVERY POWER
        # HREC power should be delivered when (1) the heat recovery is available, (2) the control signal is applied
        # and (3) relevant parameters are available: temp, temp_extr, air flow (all conditions are mandatory).
        if "hrec_pos" in op_data.keys():
            temp_diff = op_data["temp_ex"] - op_data["temp"]
            if -2.0 < temp_diff < 2.0:
                hrec_pwr_demand = 0.0
            else:
                hrec_pwr_demand = 0.79 * temp_diff * (flow_su / 3600 * 1.2 * 1005) / 1000 * 1/100 * op_data["hrec_pos"]
        else:
            hrec_pwr_demand = 0.0
        # As one could expect, demand must be gradually transformed into hrec power.
        hrec_pwr = follow_demand(hrec_pwr_demand, op_data["hrec_pwr"])

        # Finally, from flow and all heat/cool sources, the supply temperature is calculated
        if flow_su == 0.0:
            temp_su = op_data["temp_rm"]
            dust_depo = op_data["dust_depo"]
            filt_su_pres = 0.0
            filt_ex_pres = 0.0
        else:
            temp_su = op_data["temp"] + (hrec_pwr + htg_pwr - clg_pwr) * 1000 / (flow_su / 3600 * 1.2 * 1005)
            dust_depo = op_data["dust_depo"] + (1/100000000 * 2.2 * 3 * 4 * op_data["dust"])
            filt_su_pres = 1/1000000 * (flow_su ** 2) * (20 + 10 * dust_depo)
            filt_ex_pres = 1/1000000 * (flow_su ** 2) * (20 + 10 * dust_depo)
        if temp_su > 60.0:
            temp_su = 60.0
        elif temp_su < -20.0:
            temp_su = -20.0
        return {"flow_su": flow_su, "flow_ex": flow_ex, "temp_su": temp_su, "hrec_pwr": hrec_pwr, "htg_pwr": htg_pwr,
                "clg_pwr": clg_pwr, "dust_depo": dust_depo, "filt_su_pres": filt_su_pres, "filt_ex_pres": filt_ex_pres}
