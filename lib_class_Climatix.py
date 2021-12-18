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


def dust_increase(dust: float, flow: float, time: float) -> float:
    # Assumptions:
    # PM2.5 or PM10 measure refers to specific fraction of total dust in the air, approx. 1/3 of total.
    # They are given in micrograms per cubic meter.
    # Typical filters can catch up to 80% of contaminants.
    # Deposit is calculated in grams. Total mass of debris accumulated by the filter.
    deposit = 1/1000000 * 0.8 * 3 * dust * flow * time
    #             /       /      \                  \
    #            /       /        \                  \
    #     convert       /      extrapolate         script's
    #     to grams     /      all fractions        ti_diff
    #             filtering
    #             efficiency
    return deposit


def filter_curve(dust_deposit: float, air_speed: float) -> float:
    # Calculation of delta-p component that comes from the fabric.
    fabric_dp = 20 * (1/3 * air_speed ** 2 + air_speed)
    # Calculation of delta-p component that comes from the dust deposit.
    coeff = 0.2  # This coefficient adjusts how the dust deposit impacts the pressure drop.
    dust_dp = coeff * dust_deposit * (1/3 * air_speed ** 2 + air_speed)
    # Final pressure drop is a sum of those two.
    final_dp = fabric_dp + dust_dp
    return final_dp


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
        flow_sup_demand = 0.0
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
        # Additionally, air velocity in the AHU is calculated. It's proportional to flow values.
        speed_su = self.__config["ahu_spd"] * flow_su / self.__config["ahu_vol"]
        speed_ex = self.__config["ahu_spd"] * flow_ex / self.__config["ahu_vol"]

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
                hrec_pwr_demand = self.__config["hrec_eff"] * temp_diff *\
                                  (flow_su / 3600 * 1.2 * 1005) / 1000 * 1/100 * op_data["hrec_pos"]
        else:
            hrec_pwr_demand = 0.0
        # As one could expect, demand must be gradually transformed into hrec power.
        hrec_pwr = follow_demand(hrec_pwr_demand, op_data["hrec_pwr"])
        # HREC operation takes energy from extract air and alters exhaust temperature. This is calculated here.
        if flow_ex == 0.0:
            temp_eh = op_data["temp_ex"]
        else:
            temp_eh = op_data["temp_ex"] - hrec_pwr * 1000 / (flow_ex / 3600 * 1.2 * 1005)
        # And in case of extreme values, which can occur in transient conditions, temp_eh is limited to
        # relevant range
        if temp_eh > 50.0:
            temp_eh = 50.0
        elif temp_eh < -25.0:
            temp_eh = -25.0

        # Finally, from flow and all heat/cool sources, the output AHU parameters are calculated.
        if flow_su == 0.0:
            temp_su = op_data["temp_rm"]
        else:
            temp_su = op_data["temp"] + (hrec_pwr + htg_pwr - clg_pwr) * 1000 / (flow_su / 3600 * 1.2 * 1005)
        # And in case of extreme values, which can occur in transient conditions, temp_su is limited to
        # relevant range
        if temp_su > 50.0:
            temp_su = 50.0
        elif temp_su < -25.0:
            temp_su = -25.0

        # CALCULATION OF DUST DEPOSIT AND RESULTING FILTER PRESSURE DROP
        # Dust deposit is simple accumulation, depending on dust measures from API and air flow in the AHU.
        dust_depo = op_data["dust_depo"] + dust_increase(op_data["dust"], op_data["flow_su"], op_data["ti_diff"])
        # Filter pressure drop is described as f(x) ~ ⅓ξx²+ξx where x is air velocity in the filter fabrics and
        # ξ is local drag coefficient, proportional (but non-linear...?) to dust deposit.
        # Filter window can be ~15% narrower than the full AHU area - due to construction that supports filter pads.
        # Bag filters can have 7 times bigger area than AHU's cross section - thus reducing air velocity in fabrics.
        # At 7600m3/h air flow and 3x 20ug/m3 dust concentration, AHU filter catches around 0.5 grams of dust per hour.
        # 0.5 g/h >> 5.0g/day >> 100g/month >> 300g/quarter and then filters need replacement.
        # Note: not only debris causes the air flow resistance - the fabric of clean filter does it too.
        filt_su_pres = filter_curve(dust_depo, speed_su)
        filt_ex_pres = filter_curve(dust_depo, speed_ex)
        print("flow_su: {:.5}, temp_su: {:.4}, temp_eh: {:.4}, hrec_pwr: {:.4}, htg_pwr: {:.4}, clg_pwr: {:.4}, dust_depo: {:.6}".
              format(flow_su, temp_su, temp_eh, hrec_pwr, htg_pwr, clg_pwr, dust_depo))
        return {"flow_su": flow_su, "flow_ex": flow_ex, "temp_su": temp_su, "temp_eh": temp_eh, "hrec_pwr": hrec_pwr,
                "htg_pwr": htg_pwr, "clg_pwr": clg_pwr, "dust_depo": dust_depo, "filt_su_pres": filt_su_pres,
                "filt_ex_pres": filt_ex_pres}
