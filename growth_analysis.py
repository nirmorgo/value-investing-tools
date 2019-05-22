import sys
import requests
import argparse
import pandas as pd
import matplotlib.pyplot as plt
from utils import find_and_save_10K_to_folder, find_and_save_20F_to_folder, get_simfin_TTM_data
from utils import get_historical_stock_price, get_reports_list, estimate_stock_split_adjustments
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
    ratios['P/E'] = data['StockPrice'].divide(ratios['EarningPerShare(Diluted)'])

    ratios.loc['TTM'] = None
    TTM_data = get_simfin_TTM_data(ticker)
    ratios.loc['TTM']['RevenuePerShare(Diluted)'] = TTM_data['Revenues'] / \
        TTM_data['Average Shares Outstanding, diluted']
    ratios.loc['TTM']['EarningPerShare(Diluted)'] = TTM_data['Earnings per Share, Diluted']
    ratios.loc['TTM']['BookValuePerShare'] = TTM_data['Book Value per Share']
    ratios.loc['TTM']['FreeCashFlowPerShare(Diluted)'] = TTM_data['Free Cash Flow'] / \
        TTM_data['Average Shares Outstanding, diluted']
    ratios.loc['TTM']['P/E'] = TTM_data['Price to Earnings Ratio']

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
    print('-----------------------------------------------------------------')
    print('----------------------Fundamental data:--------------------------')
    print('-----------------------------------------------------------------')
    print(data.transpose())
    print('-----------------------------------------------------------------')
    print('--------------------Key growth indicators:-----------------------')
    print('-----------------------------------------------------------------')
    ratios = calculate_ratios(data, ticker)

    print(ratios.transpose())
    set_trace()


if __name__ == "__main__":
    main()
