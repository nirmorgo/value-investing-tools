# This script will download all the 10-K, 10-Q and 8-K
# provided that of company symbol and its cik code.
# shamelessly borrowed from https://github.com/coyo8/sec-edgar and slightly modified
# so it can scrape for xbrl files instead of txt

from __future__ import print_function  # Compatibility with Python 2

import requests
import os
import errno
from bs4 import BeautifulSoup
import datetime
from ipdb import set_trace
import re

DEFAULT_DATA_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '.', 'SEC-Edgar-Data'))


class SecCrawler(object):

    def __init__(self, data_path=DEFAULT_DATA_PATH):
        self.data_path = data_path
        print("Path of the directory where data will be saved: " + self.data_path)

    def __repr__(self):
        return "SecCrawler(data_path={0})".format(self.data_path)

    def _make_directory(self, company_code, priorto, filing_type):
        # Making the directory to save comapny filings
        self.full_path = os.path.join(
            self.data_path, company_code, filing_type)

        if not os.path.exists(self.full_path):
            try:
                os.makedirs(self.full_path)
            except OSError as exception:
                if exception.errno != errno.EEXIST:
                    raise

    def _save_in_directory(self, docs):
        # Save every text document into its respective folder
        for (url, doc_name) in docs:
            r = requests.get(url)
            data = r.text
            path = os.path.join(self.full_path, doc_name)
            with open(path, "ab") as f:
                f.write(data.encode('ascii', 'ignore'))

    def _save_links_summary(self, link_list):
        path = os.path.join(self.full_path, 'links.txt')
        with open(path, 'w') as f:
            for item in link_list:
                f.write("%s\n" % item)

    def _find_xbrl_link(self, base_url):
        with requests.get(base_url) as r:
            data = r.text
        soup = BeautifulSoup(data, features='html.parser')
        # store the link in the list
        link_list = [link.string for link in soup.find_all('a')]
        regex = re.compile('.*[0-9].xml')
        file_name, file_url = None, None
        for link in link_list:
            if link is not None and regex.match(link):
                file_name = link
                # replace last part of the link with the xml file name
                file_url = '/'.join(base_url.split('/')[:-1] + [link])
        # set_trace()
        return file_url, file_name

    def _create_document_list(self, data, doc_type='txt'):
        # parse fetched data using beatifulsoup
        # Explicit parser needed
        soup = BeautifulSoup(data, features='html.parser')
        # store the link in the list
        link_list = [link.string for link in soup.find_all('filinghref')]

        self._save_links_summary(link_list)
        print("Number of files to download: {0}".format(len(link_list)))
        print("Starting download...")

        # List of url to the text documents
        if doc_type == 'txt':
            txt_urls = [link[:link.rfind("-")] + ".txt" for link in link_list]
            # List of document doc_names
            doc_names = [url.split("/")[-1] for url in txt_urls]
            return list(zip(txt_urls, doc_names))

        elif doc_type == 'xbrl':
            xbrl_urls, doc_names = [], []
            for link in link_list:
                xbrl_url, doc_name = self._find_xbrl_link(link)
                if xbrl_url is not None:
                    xbrl_urls.append(xbrl_url)
                    doc_names.append(doc_name)
                # set_trace()
            return list(zip(xbrl_urls, doc_names))

    def _sanitize_date(self, date):
        if isinstance(date, datetime.datetime):
            return date.strftime("%Y%m%d")
        elif isinstance(date, str):
            if len(date) != 8:
                raise TypeError('Date must be of the form YYYYMMDD')
        elif isinstance(date, int):
            if date < 10**7 or date > 10**8:
                raise TypeError('Date must be of the form YYYYMMDD')

    def _fetch_report(self, company_code, cik, priorto, count, filing_type, doc_type='txt'):
        priorto = self._sanitize_date(priorto)
        self._make_directory(company_code, priorto, filing_type)

        # generate the url to crawl
        base_url = "http://www.sec.gov/cgi-bin/browse-edgar"
        params = {'action': 'getcompany', 'owner': 'exclude', 'output': 'xml',
                  'CIK': cik, 'type': filing_type, 'dateb': priorto, 'count': count}
        print("started {filing_type} {company_code}".format(
            filing_type=filing_type, company_code=company_code))
        with requests.get(base_url, params=params) as r:
            data = r.text

        # get doc list data
        docs = self._create_document_list(data, doc_type)

        try:
            self._save_in_directory(docs)
        except Exception as e:
            print(str(e))  # Need to use str for Python 2.5

        print("Successfully downloaded {0} files ".format(len(docs)))

    def filing_10Q(self, company_code, cik, priorto, count, doc_type='txt'):
        self._fetch_report(company_code, cik, priorto, count, '10-Q', doc_type)

    def filing_10K(self, company_code, cik, priorto, count, doc_type='txt'):
        self._fetch_report(company_code, cik, priorto, count, '10-K', doc_type)

    def filing_8K(self, company_code, cik, priorto, count, doc_type='txt'):
        self._fetch_report(company_code, cik, priorto, count, '8-K', doc_type)

    def filing_13F(self, company_code, cik, priorto, count, doc_type='txt'):
        self._fetch_report(company_code, cik, priorto, count, '13-F', doc_type)
    
    def filing_20F(self, company_code, cik, priorto, count, doc_type='txt'):
        self._fetch_report(company_code, cik, priorto, count, '20-F', doc_type)

    def filing_SD(self, company_code, cik, priorto, count, doc_type='txt'):
        self._fetch_report(company_code, cik, priorto, count, 'SD', doc_type)

    def filing_4(self, company_code, cik, priorto, count, doc_type='txt'):
        self._fetch_report(company_code, cik, priorto, count, '4', doc_type)
