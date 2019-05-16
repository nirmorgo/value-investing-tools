from crawler import SecCrawler
import re
import requests
import os
import sys
from datetime import datetime


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
    url = "http://d.yimg.com/autoc.finance.yahoo.com/autoc?query={}&region=1&lang=en".format(
        ticker)
    result = requests.get(url).json()
    for x in result['ResultSet']['Result']:
        if x['symbol'] == ticker:
            return x['name']
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
