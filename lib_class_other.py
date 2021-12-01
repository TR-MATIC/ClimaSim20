# packages
# import requests
# from datetime import datetime
import time


# defs
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
        line = "{}".format(time.strftime("%Y.%m.%d %H:%M"))
        for key in op_data:
            if op_data[key] in (True, False):
                line = line + ";{}={}".format(key, op_data[key])
            elif key in ("error"):
                line = line + ";{}={}".format(key, op_data[key])
            else:
                line = line + ";{}={:.3f}".format(key, op_data[key])
        line = line + "\n"
        report_file.writelines(line)
        report_file.close()
        return True


def load_config(config_path: str) -> dict:
    config_file = open(config_path, mode="r")
    config_data = config_file.readlines()
    config_file.close()
    config = {}
    for line in config_data:
        marker = line.find("=")   # It finds the first occurence of "=" character
        key = line[0:marker]   # What's before that marker, will become a key and what follows after, will be a value.
        # However, script must recognize if it's loading string or numerical value, hence additional condition.
        if line[(marker + 1)] == "(":
            value = float(line[(marker + 2):].rstrip(")\n"))
        else:
            value = line[(marker + 1):].rstrip("\n")
        config.update({key: value})    # Finally, the "config" dictionary is updated with new entry.
    return config
