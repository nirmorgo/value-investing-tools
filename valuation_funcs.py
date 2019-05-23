import numpy as np
import pandas as pd

def calculate_cagr(start_value, end_value, years):
    cagr = ((end_value / start_value) ** (1 / years) - 1)
    return int(np.round(cagr * 100))

def calculate_cagr_of_time_series(input_series):
    if input_series.index[-1] == 'TTM':
        values = input_series.iloc[:-1]
    else:
        values = input_series
    current_year = values.index[-1]
    current_value = values.iloc[-1]
    periods = []
    cagrs = []
    for idx, value in enumerate(values.iloc[:-1]):
        periods.append(current_year - values.index[idx])
        try:
            cagr = calculate_cagr(value, current_value, periods[-1])
            cagrs.append(str(cagr)+"%")
        except:
            cagrs.append(None)

    cagrs.append(np.nan)
    
    columns = [str(period) + ' yeras' for period in periods] + ['now']
    out = pd.DataFrame(columns=columns, index=['value','CAGR'])
    out.loc['value'] = values.values
    out.loc['CAGR'] = cagrs
    return out