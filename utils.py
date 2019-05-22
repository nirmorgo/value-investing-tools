from crawler import SecCrawler
import re
import requests
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
# add config.py file which contains https://www.worldtradingdata.com/ and https://simfin.com/data/access/api API keys
from config import WTD_api_key, simfin_api_key


def find_and_save_10K_to_folder(ticker, from_date=None, number_of_documents=40, doc_type='xbrl'):
    if from_date is None:
        from_date = datetime.today().strftime('%Y%m%d')
    crawler = SecCrawler()
    cik = get_cik_from_ticker(ticker)
    crawler.filing_10K(ticker, cik, from_date, number_of_documents, doc_type)


def find_and_save_10Q_to_folder(ticker, from_date=None, number_of_documents=40, doc_type='xbrl'):
    if from_date is None:
        from_date = datetime.today().strftime('%Y%m%d')
    crawler = SecCrawler()
    cik = get_cik_from_ticker(ticker)
    crawler.filing_10Q(ticker, cik, from_date, number_of_documents, doc_type)


def find_and_save_20F_to_folder(ticker, from_date=None, number_of_documents=40, doc_type='xbrl'):
    if from_date is None:
        from_date = datetime.today().strftime('%Y%m%d')
    crawler = SecCrawler()
    cik = get_cik_from_ticker(ticker)
    crawler.filing_20F(ticker, cik, from_date, number_of_documents, doc_type)


def get_cik_from_ticker(ticker):
    URL = 'http://www.sec.gov/cgi-bin/browse-edgar?CIK={}&Find=Search&owner=exclude&action=getcompany'.format(
        ticker)
    CIK_RE = re.compile(r'.*CIK=(\d{10}).*')
    results = CIK_RE.findall(requests.get(URL).content.decode('utf-8'))
    if type(results) == str:
        return results
    elif type(results) == list:
        return str(results[0])
    else:
        print('could not find cik number...')
        return None


def get_name_from_ticker(ticker):
    request_url = f'https://simfin.com/api/v1/info/find-id/ticker/{ticker}?api-key={simfin_api_key}'
    content = requests.get(request_url)
    content = content.json()
    try:
        name = content[0]['name']
        return name
    except:
        print('couldnt find company name....')
        return None


def get_reports_list(ticker, report_type='10-K', file_type='xbrl', data_folder='./SEC-Edgar-Data/'):
    report_type += '/'
    path = os.path.join(data_folder, ticker, report_type)
    if not os.path.isdir(path):
        print(f'could not find {ticker} folder')
        sys.exit()
    if file_type == 'xbrl':
        files = [os.path.join(path, f) for f in os.listdir(
            path) if re.match(r'.*[0-9]+.xml', f)]
    elif file_type == 'txt':
        files = [os.path.join(path, f) for f in os.listdir(
            path) if re.match(r'.*[0-9]+.txt', f)]

    return files


def get_historical_stock_price(ticker, years=10, api='WTD'):
    '''
    use world trading data to get stock price history (need to have api key set in config.py file) 
    '''
    start_date = (datetime.now() - timedelta(days=years*365)
                  ).strftime('%Y-%m-%d')
    if api == 'WTD':
        request_url = f'https://www.worldtradingdata.com/api/v1/history?symbol={ticker}&sort=newest&api_token={WTD_api_key}&date_from={start_date}'
        content = requests.get(request_url)
        data = content.json()
        df = pd.DataFrame.from_dict(data['history'], orient='index')
        df.index = pd.to_datetime(df.index)
        df = df.apply(pd.to_numeric, errors='coerce')
    return df


def estimate_stock_split_adjustments(stock_count):
    '''
    gets a series of stock prices, estimates if there were major stock splits
    returns an adjusted stock_count
    '''
    multiplier = 1
    counts = stock_count.values
    adjusted_count = pd.Series(0, index=stock_count.index)
    adjusted_count.iloc[-1] = counts[-1]
    for idx, count in reversed(list(enumerate(counts[:-1]))):
        ratio = stock_count.iloc[idx + 1] / count
        if ratio > 1.7:  # assuming that the split is an integer > 2
            multiplier *= np.round(ratio)
        adjusted_count.iloc[idx] = count * multiplier

    return adjusted_count


def get_simfin_TTM_data(ticker):
    '''
    use simfin API to get TTM data (need to have api key set in config.py file) 
    '''
    request_url = f'https://simfin.com/api/v1/info/find-id/ticker/{ticker}?api-key={simfin_api_key}'
    content = requests.get(request_url)
    content = content.json()
    sim_id = content[0]['simId']
    request_url = f'https://simfin.com/api/v1/companies/id/{sim_id}/ratios?api-key={simfin_api_key}'
    content = requests.get(request_url)
    content = content.json()
    TTM_data = {}
    for ratio in content:
        TTM_data[ratio['indicatorName']] = float(ratio['value'])

    return TTM_data
