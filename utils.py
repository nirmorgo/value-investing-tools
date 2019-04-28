from crawler import SecCrawler
import re
import requests


def find_and_save_10k_to_folder(ticker, from_date='20190401', type="10-K", path='./SEC-Edgar-data/', number_of_documents=5):
    crawler = SecCrawler()
    cik = get_cik_from_ticker(ticker)
    crawler.filing_10K(ticker, cik, from_date, number_of_documents)



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
