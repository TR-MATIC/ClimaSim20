# packages
from lib_class import Ambient, Building, Climatix


# constants
# All stored in TXT files


# climatic_auth = (climatix_name, climatix_pass)
# climatix_params_write = {"fn": "write"}
# climatix_params_read = {"fn": "read"}


# code
outside_con = Ambient()
outside_con.load_config()
outside_con.create_meteo_headers()
outside_con.get_coordinates()
outside_con.get_dates()
outside_con.renew_forecast()
outside_con.renew_dust_measure()
outside_con.simulate_ambient()
