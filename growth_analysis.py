import sys
import requests
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from utils import find_and_save_10K_to_folder, get_simfin_TTM_data
from utils import get_historical_stock_price, get_reports_list, estimate_stock_split_adjustments
from valuation_funcs import calculate_cagr_of_time_series, growth_at_normalized_PE
from xbrl_parser import XBRL
from ipdb import set_trace

parser = argparse.ArgumentParser(description='Optional app description')
parser.add_argument('--ticker', '-t', type=str,
                    help='The ticker of the stock you wish to analyze')
parser.add_argument('--download', '-d', action='store_true',
                    help='A boolean switch')

args = parser.parse_args()


def load_all_historical_data(ticker, download_latest=True):
    ticker = ticker.lower()
    if download_latest:
        find_and_save_10K_to_folder(ticker)
    files = get_reports_list(ticker)
    if len(files) <= 1:
        print(f'could not find enough {ticker} data')
        sys.exit()
    xbrl = XBRL()
    for file in files:
        xbrl.load_xbrl_file(file)
    return xbrl.get_data_df()


def calculate_ratios(data, ticker):
    ratios = pd.DataFrame()
    ratios['RevenuePerShare(Diluted)'] = data['Revenues'].divide(
        data['NumberOfDilutedSharesAdjusted'])
    ratios['EarningPerShare(Diluted)'] = data['NetIncomeLoss'].divide(
        data['NumberOfDilutedSharesAdjusted'])
    ratios['BookValuePerShare'] = data['StockholdersEquity'].divide(
        data['NumberOfSharesAdjusted'])
    ratios['FreeCashFlowPerShare(Diluted)'] = (data['CashFlowFromOperations'] -
                                               data['CapitalExpenditure']).divide(data['NumberOfDilutedSharesAdjusted'])
    ratios['P/E'] = data['StockPrice'].divide(
        ratios['EarningPerShare(Diluted)'])

    ratios.loc['TTM'] = None
    TTM_data = get_simfin_TTM_data(ticker)
    try:
        ratios.loc['TTM']['RevenuePerShare(Diluted)'] = TTM_data['Revenues'] / \
            TTM_data['Average Shares Outstanding, diluted']
    except:
        pass
    try:
        ratios.loc['TTM']['EarningPerShare(Diluted)'] = TTM_data['Earnings per Share, Diluted']
    except:
        pass
    try:
        ratios.loc['TTM']['BookValuePerShare'] = TTM_data['Book Value per Share']
    except:
        pass
    try:
        ratios.loc['TTM']['FreeCashFlowPerShare(Diluted)'] = TTM_data['Free Cash Flow'] / \
            TTM_data['Average Shares Outstanding, diluted']
    except:
        pass
    try:
        ratios.loc['TTM']['P/E'] = TTM_data['Price to Earnings Ratio']
    except:
        pass
    return ratios


def main():
    ticker = args.ticker
    data = load_all_historical_data(ticker, download_latest=args.download)
    data = data.iloc[1:]

    data['NumberOfDilutedSharesAdjusted'] = estimate_stock_split_adjustments(
        data['NumberOfDilutedShares'])
    data['NumberOfSharesAdjusted'] = estimate_stock_split_adjustments(
        data['NumberOfShares'])

    years = int(data.index[-1] - data.index[0] + 1)
    daily_prices = get_historical_stock_price(ticker, years)

    monthly_prices = daily_prices.close.resample('M').last()
    monthly_idxs = monthly_prices.index.to_list()
    # the last sample should be of the current date
    monthly_idxs[-1] = daily_prices.index[-1]
    monthly_prices.index = monthly_idxs

    yearly_prices = daily_prices.close.resample('Y').last()
    yearly_prices.drop(yearly_prices.tail(1).index, inplace=True)
    yearly_prices.index = yearly_prices.index.year

    data['StockPrice'] = yearly_prices
    print('-------------------------------------------------------------------------------------')
    print('--------------------------------Fundamental data:------------------------------------')
    print('-------------------------------------------------------------------------------------')
    print(data.transpose())
    print()
    print('-------------------------------------------------------------------------------------')
    print('------------------------------Key growth indicators:---------------------------------')
    print('-------------------------------------------------------------------------------------')
    ratios = calculate_ratios(data, ticker)

    print(ratios.transpose())
    print()
    print('-------------------------------------------------------------------------------------')
    print('Revenue Per Share (Diluted) Growth:')
    revenue_per_share_growth = calculate_cagr_of_time_series(
        ratios['RevenuePerShare(Diluted)'])
    print(revenue_per_share_growth)
    print()
    print('-------------------------------------------------------------------------------------')
    print('Earning PerShare (Diluted) Growth:')
    eps_growth = calculate_cagr_of_time_series(
        ratios['EarningPerShare(Diluted)'])
    print(eps_growth)
    print()
    print('-------------------------------------------------------------------------------------')
    print('Book Value Per Share Growth:')
    book_value_per_share_growth = calculate_cagr_of_time_series(
        ratios['BookValuePerShare'])
    print(book_value_per_share_growth)
    print()
    print('-------------------------------------------------------------------------------------')
    print('Free Cash Flow Per Share (Diluted) Growth:')
    free_cash_flow_growth = calculate_cagr_of_time_series(
        ratios['FreeCashFlowPerShare(Diluted)'])
    print(free_cash_flow_growth)
    print('-------------------------------------------------------------------------------------')
    print()
    print()
    print('Value estimation with "Growth At Normalized P/E" technique:')
    print('-------------------------------------------------------------------------------------')
    GR_estimation = input(
        'Estimate growth rate in % (if nothing entered, avarage growth is taken): ')
    if GR_estimation == '':
        cagrs = revenue_per_share_growth.loc['CAGR'].values.tolist() + eps_growth.loc['CAGR'].values.tolist(
        ) + book_value_per_share_growth.loc['CAGR'].values.tolist() + free_cash_flow_growth.loc['CAGR'].values.tolist()
        valid_cagrs = []
        for cagr in cagrs:
            try:
                cagr_value = int(cagr[:-1])
                valid_cagrs.append(cagr_value)
            except:
                continue
        # capping the growth rate estimation in 5-20% range
        GR_estimation = min(max(np.mean(valid_cagrs), 5), 20)
    GR_estimation = int(GR_estimation)
    normalized_pe_estimation = input(
        "Estimate normalized P/E estimation (if nothing entered, estimation will be done according to the median p/e):")
    if normalized_pe_estimation == '':
        pes = ratios['P/E'].values
        pes = pes[~np.isnan(pes)]
        normalized_pe_estimation = max(np.median(pes), 5) * 1.2
    normalized_pe_estimation = float(normalized_pe_estimation)
    eps_ttm = ratios.loc['TTM']['EarningPerShare(Diluted)']
    print("Growth rate estimation: %d%%, future P/E estimation: %.2f" %
          (GR_estimation, normalized_pe_estimation))
    print("Fair value is estimated in the range of $%.2f - $%.2f" %
          (growth_at_normalized_PE(eps_ttm, normalized_pe_estimation, GR_estimation)))

    print('-------------------------------------------------------------------------------------')
    print()
    print()


if __name__ == "__main__":
    main()
