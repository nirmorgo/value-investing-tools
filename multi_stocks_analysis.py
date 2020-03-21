import sys
import requests
import argparse
import pandas as pd
import numpy as np

from growth_analysis import load_all_historical_10K, load_latest_quarters, calculate_key_values, get_TTM_data
from utils import get_historical_stock_price, get_reports_list, estimate_stock_split_adjustments, get_cik_and_name_from_ticker
from valuation_funcs import calculate_cagr_of_time_series, calc_growth_at_normalized_PE, calc_owner_earnings, DCF_FCF, calculate_ROIC

TICKERS = ["THO", "V", "MA", "FB", "MSFT", "MU", "AAPL", "QCOM", "AMAT", "FDX", "AMZN", "NFLX", "KLAC", "BKNG", "CSCK",
           "INTU", "TXN", "TMO", "A", "DHR", "SPOT", "ZOOM", "SLACK", "OKTA", "ROKU", "INTC", "PINS", "GOOG", "SPLK", "BABA",
           "LK", "FVRR", "LAC", "SBUX", "DAL", "JPM", "PNC", "SEDG", "PFSI", "ENPH", "OLED", "NVDA"]

def main():	
    output = pd.DataFrame(columns=["company name", "ticker", "value at normalized p/e growth", 
                                   "Owner earnings ratio (>1.0 is good)", "value at discounted cash flow",
                                   "last price", "buy indicators", "growth estimation", "p/e estimation"])
    for ticker in TICKERS:
        buy_indicators = 0
        out = {}
        try:
            _, comp_name = get_cik_and_name_from_ticker(ticker)
            out["ticker"] = ticker
            out["company name"] = comp_name
            data = load_all_historical_10K(ticker.lower())
            data = data.iloc[1:]
            data.loc['TTM'] = get_TTM_data(ticker.lower())
        except Exception:
            print("couldn't find proper data for %s... skipping it!" % ticker)
            output = output.append({"ticker": ticker}, ignore_index=True)
            continue
        data['NumberOfDilutedSharesAdjusted'] = estimate_stock_split_adjustments(
            data['NumberOfDilutedShares'])
        data['NumberOfSharesAdjusted'] = estimate_stock_split_adjustments(
            data['NumberOfShares'])
        data['NumberOfDilutedSharesAdjusted'].fillna(
            data['NumberOfSharesAdjusted'], inplace=True)
        data = data.iloc[-10:] # use only data from last decade
        
        print("Analyzing.............")
        years = int(data.index[-2] - data.index[0] + 1)
        daily_prices = get_historical_stock_price(ticker, years)
        out["last price"] = daily_prices.iloc[-1].close

        monthly_prices = daily_prices.close.resample('M').last()
        monthly_idxs = monthly_prices.index.to_list()
        # the last sample should be of the current date
        monthly_idxs[-1] = daily_prices.index[-1]
        monthly_prices.index = monthly_idxs

        yearly_prices = daily_prices.close.resample('Y').last()
        yearly_prices.drop(yearly_prices.tail(1).index, inplace=True)
        yearly_prices.index = yearly_prices.index.year

        data['StockPrice'] = yearly_prices
        data.loc['TTM']['StockPrice'] = daily_prices.iloc[-1].close

        # ------------------------------Key growth indicators:---------------------------------
        key_values = calculate_key_values(data)
        book_value_per_share_growth = calculate_cagr_of_time_series(key_values['BookValuePerShare'])
        eps_growth = calculate_cagr_of_time_series(key_values['EarningPerShare(Diluted)'])
        oi_growth = calculate_cagr_of_time_series(key_values['OI (or EBIT)'])
        revenue_per_share_growth = calculate_cagr_of_time_series(key_values['RevenuePerShare(Diluted)'])
        free_cash_flow_growth = calculate_cagr_of_time_series(key_values['FreeCashFlowPerShare(Diluted)'])

        # ----------Value estimation with "Growth At Normalized P/E" technique-----------------
        cagrs = revenue_per_share_growth.loc['CAGR'].values.tolist() + eps_growth.loc['CAGR'].values.tolist(
        ) + book_value_per_share_growth.loc['CAGR'].values.tolist() + free_cash_flow_growth.loc['CAGR'].values.tolist(
        ) + oi_growth.loc['CAGR'].values.tolist()
        valid_cagrs = []
        for cagr in cagrs:
            try:
                cagr_value = int(cagr[:-1])
                valid_cagrs.append(cagr_value)
            except:
                continue
        try:
            # capping the default growth rate estimation in 5-10% range
            GR_default = min(max(np.mean(valid_cagrs), 5), 10)
            GR_estimation = int(GR_default)
            out["growth estimation"] = "%d%%" % int(GR_estimation)
            pes = key_values['P/E'].values
            pes = pes[~np.isnan(pes)]
            default_pe_estimation = max(np.median(pes), 5) * 1.1
            normalized_pe_estimation = float(default_pe_estimation)
            out["p/e estimation"] = np.round(normalized_pe_estimation, 2)
            eps_ttm = key_values.loc['TTM']['EarningPerShare(Diluted)']
            if np.isnan(eps_ttm):
                eps_ttm = key_values.iloc[-2]['EarningPerShare(Diluted)']
            norm_pe_min, norm_pe_max = calc_growth_at_normalized_PE(eps_ttm, normalized_pe_estimation, GR_estimation)
            if norm_pe_min >= 1.5 * out["last price"]:
                buy_indicators += 1
            out["value at normalized p/e growth"] = "$%d-%d" % (int(norm_pe_min), int(norm_pe_max))
        except:
            out["value at normalized p/e growth"] = "NaN"

        # ---------------Value estimation with "Owner Earnings" technique------------------------
        try:
            owner_earnings = calc_owner_earnings(data.iloc[-2])
            market_cap = daily_prices.iloc[-1].close * \
                data.iloc[-2]['NumberOfShares']
            owner_earnings_ratio = np.round(10 * owner_earnings / market_cap, 2)
            if owner_earnings_ratio >= 0.75:
                buy_indicators += 1
            out["Owner earnings ratio (>1.0 is good)"] = owner_earnings_ratio
        except:
            out["Owner earnings ratio (>1.0 is good)"] = "NaN"

        # -----------Value estimation with "Discounted Cash Flow (FCF based)" technique----------
        FCF_cagrs = free_cash_flow_growth.loc['CAGR'].values
        valid_cagrs = []
        for cagr in FCF_cagrs:
            try:
                cagr_value = int(cagr[:-1])
                valid_cagrs.append(cagr_value)
            except:
                continue
        # capping the default growth rate estimation in 5-20% range
        if len(valid_cagrs) > 0:
            FCF_GR = min(max(np.mean(valid_cagrs), 5), 20)
        else:
            FCF_GR = GR_default
        try:
            latest_FCF = key_values['FreeCashFlowPerShare(Diluted)'].dropna().iloc[-1]
            dcf_low, dcf_high = DCF_FCF(latest_FCF, growth_rate=FCF_GR)
            if dcf_low >= 1.5 * out["last price"]:
                buy_indicators += 1
            out["value at discounted cash flow"] = "$%d-%d" % (int(dcf_low), int(dcf_high))
        except:
            out["value at discounted cash flow"] = "NaN"

        out["buy indicators"] = buy_indicators
        output = output.append(out, ignore_index=True)
        print(out)

    print(output)
    output.to_csv("stocks_summary.csv", encoding='utf-8')



if __name__ == "__main__":
    main()
