import numpy as np
import pandas as pd

def sec_to_ms(sec):
    if sec is None:
        return None
    elif type(sec) in [np.ndarray, pd.core.series.Series]:
        return sec * 1000
    elif type(sec) == list:
        return [i * 1000 for i in sec]
    else:
        return sec * 1000

def min_to_sec(min):
    if min is None:
        return None
    elif type(min) in [np.ndarray, pd.core.series.Series]:
        return min * 60
    elif type(min) == list:
        return [i * 60 for i in min]
    else:
        return min * 60

def ms_to_min(ms):
    if ms is None:
        return None
    elif type(ms) in [np.ndarray, pd.core.series.Series]:
        return ms / 60000
    elif type(ms) == list:
        return [i / 60000 for i in ms]
    else:
        return ms / 60000

def sec_to_min(sec):
    if sec is None:
        return None
    elif type(sec) in [np.ndarray, pd.core.series.Series]:
        return sec / 60
    elif type(sec) == list:
        return [i / 60 for i in sec]
    else:
        return sec / 60

def ms_to_sec(ms):
    if ms is None:
        return None
    elif type(ms) in [np.ndarray, pd.core.series.Series]:
        return ms / 1000
    elif type(ms) == list:
        return [i / 1000 for i in ms]
    else:
        return ms / 1000

def hr_to_ms(hr):
    if hr is None:
        return None
    elif type(hr) in [np.ndarray, pd.core.series.Series]:
        return hr * 3600000
    elif type(hr) == list:
        return [i * 3600000 for i in hr]
    else:
        return hr * 3600000

def sec_to_hr(sec):
    if sec is None:
        return None
    elif type(sec) in [np.ndarray, pd.core.series.Series]:
        return sec / 3600
    elif type(sec) == list:
        return [i / 3600 for i in sec]
    else:
        return sec / 3600

def ms_to_hr(ms):
    if ms is None:
        return None
    elif type(ms) in [np.ndarray, pd.core.series.Series]:
        return ms / 3600000
    elif type(ms) == list:
        return [i / 3600000 for i in ms]
    else:
        return ms / 3600000

def ft_to_m(ft):
    if ft is None:
        return None
    elif type(ft) in [np.ndarray, pd.core.series.Series]:
        return ft * 0.3048
    elif type(ft) == list:
        return [i * 0.3048 for i in ft]
    else:
        return ft * 0.3048

def m_to_ft(m):
    if m is None:
        return None
    elif type(m) in [np.ndarray, pd.core.series.Series]:
        return m / 0.3048
    elif type(m) == list:
        return [i / 0.3048 for i in m]
    else:
        return m / 0.3048

def miles_to_m(miles):
    if miles is None:
        return None
    elif type(miles) in [np.ndarray, pd.core.series.Series]:
        return miles * 1609.34
    elif type(miles) == list:
        return [i * 1609.34 for i in miles]
    else:
        return miles * 1609.34

def mph_to_metersec(mph):
    if mph is None:
        return None
    elif type(mph) in [np.ndarray, pd.core.series.Series]:
        return mph * 0.44704
    elif type(mph) == list:
        return [i * 0.44704 for i in mph]
    else:
        return mph * 0.44704

def metersec_to_mph(metersec):
    if metersec is None:
        return None
    elif type(metersec) in [np.ndarray, pd.core.series.Series]:
        return metersec / 0.44704
    elif type(metersec) == list:
        return [i / 0.44704 for i in metersec]
    else:
        return metersec / 0.44704

def watt_to_kw(watt):
    if watt is None:
        return None
    elif type(watt) in [np.ndarray, pd.core.series.Series]:
        return watt / 1000
    elif type(watt) == list:
        return [i / 1000 for i in watt]
    else:
        return watt / 1000

def kw_to_watt(kw):
    if kw is None:
        return None
    elif type(kw) in [np.ndarray, pd.core.series.Series]:
        return kw * 1000
    elif type(kw) == list:
        return [i * 1000 for i in kw]
    else:
        return kw * 1000

def degrees_to_radians(degrees):
    if degrees is None:
        return None
    if type(degrees) in [np.ndarray, pd.core.series.Series]:
        return degrees * 0.0174533
    elif type(degrees) == list:
        return [i * 0.0174533 for i in degrees]
    else:
        return degrees * 0.0174533
