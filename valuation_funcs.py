import numpy as np
import pandas as pd


def calculate_ROIC(data):
    """gets a data frame with the following fields: OperatingIncome, TaxRate, LongTermDebt, CurrentDebt, StockholderEquity and Cash
        and calculate the ROIC of the company per year
    
    Arguments:
        data {pd.Dataframe} -- Dataframe with all needed columns
    """
    nopat = data['OperatingIncomeLoss'] * (1 - data['TaxRate'])
    long_term_debt = data['LongTermDebt'].fillna(0)
    current_debt = data['CurrentDebt'].fillna(0)
    invested_capital = long_term_debt + current_debt + data['StockholdersEquity'] - data['Cash']
    average_invested_capital = [None]
    for i in range(len(invested_capital))[1:]:
        average = (invested_capital.iloc[i] + invested_capital.iloc[i - 1]) / 2
        average_invested_capital.append(average)
    
    roic_values = nopat.divide(average_invested_capital)
    roic = pd.Series([f"{round(100 * val, 2)}%" for val in roic_values], index=roic_values.index)
    return roic


def calculate_cagr(start_value, end_value, years):
    if start_value <= 0 or end_value <= 0:
        return None
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
    out = pd.DataFrame(columns=columns, index=['value', 'CAGR'])
    out.loc['value'] = values.values
    out.loc['CAGR'] = cagrs
    return out


def calc_growth_at_normalized_PE(eps_ttm, normalized_pe_estimation, GR_estimation):
    '''
    a nice valuation technique where we predict a fair price for the stock by projecting the stimated growth 
    values, and then calculate it back (with a discount rate)
    '''
    # calculate 12% dicount rate for 6 years
    future_eps = eps_ttm * np.power((1 + GR_estimation / 100.0), 6)
    discounted_eps = future_eps / np.power(1.12, 6)
    high_value = discounted_eps * normalized_pe_estimation

    # calculate 15% dicount rate for 6 years
    future_eps = eps_ttm * np.power((1 + GR_estimation / 100.0), 5)
    discounted_eps = future_eps / np.power(1.15, 5)
    low_value = discounted_eps * normalized_pe_estimation

    return low_value, high_value


def calc_owner_earnings(last_year_data):
    '''
    a valuation technique where we calculate the owner earnings from the buisness operation
    The assumption is that if the market cap is higher than 10 years of earnings, than the 
    stock might be overpriced.
    the function gets the income statement data, and returns the owner earnings
    '''
    balance = {}
    balance['income'] = last_year_data['NetIncomeLoss']
    balance['tax'] = last_year_data['IncomeTaxExpenseBenefit']
    balance['deprecation'] = last_year_data['DepreciationAndAmortization']
    balance['recievables'] = last_year_data['IncreaseDecreaseInAccountsReceivable']
    balance['payable'] = last_year_data['IncreaseDecreaseInAccountsPayable']
    balance['capex'] = last_year_data['CapitalExpenditure']

    for key in balance.keys():
        if np.isnan(balance[key]):
            balance[key] = 0
            if key in ['income', 'capex']:
                print('Not enough information for owner earnings calculation')
                return None

    owner_earnings = balance['income'] + balance['tax'] + balance['deprecation'] - \
        balance['recievables'] + balance['payable'] - balance['capex']
    
    return owner_earnings
    

def DCF_FCF(latest_fcf, growth_rate=20):
    '''
    Discounted Cash Flow model based on Free Cash Flow (As described in https://www.gurufocus.com/)
    The future cash flow is estimated based on a cash flow growth rate and a discount rate. 
    All of the discounted future cash flow is added together to get the current intrinsic value of the company.
    We use a two-stage model when calculating a stock's intrinsic value - a growth stage with high growth and a terminal stage with slower growth
    Here I do the estimation twice with different growth rates to get a low / high bounds.
    '''
    if latest_fcf <= 0:
        return None, None
    
    growth_rate /= 100  # change percents to fractions
    d = 0.12  # Discount rate
    terminal_growth_rate = 0.04
    y1 = 10  # years at high growth rate
    y2 = 10  # years  at the terminal stage
    accumulated_ratios = 0
    for y in range(y1+1)[1:]:
        g_2_d_ratio = np.power((1 + growth_rate) / (1 + d), y)
        accumulated_ratios += g_2_d_ratio
    
    for y in range(y2+1)[1:]:
        terminal_ratio = np.power((1 + terminal_growth_rate) / (1 + d), y)
        accumulated_ratios += g_2_d_ratio * terminal_ratio

    high_DCF = latest_fcf * accumulated_ratios

    # do a lower estimation with slower growth rate
    low_growth_rate = max(0.05, growth_rate / 2)
    accumulated_ratios = 0
    for y in range(y1+1)[1:]:
        g_2_d_ratio = np.power((1 + low_growth_rate) / (1 + d), y)
        accumulated_ratios += g_2_d_ratio
    
    for y in range(y2+1)[1:]:
        terminal_ratio = np.power((1 + terminal_growth_rate) / (1 + d), y)
        accumulated_ratios += g_2_d_ratio * terminal_ratio

    low_DCF = latest_fcf * accumulated_ratios

    return low_DCF, high_DCF


