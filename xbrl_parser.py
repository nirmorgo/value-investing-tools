# from lxml import etree
import re
from bs4 import BeautifulSoup
from ipdb import set_trace
import pandas as pd
from datetime import datetime


class XBRL:

    def __init__(self, xbrl_path=None, extra_tags=[]):

        self.data = {}
        self.YTD_contexts = {}
        self.Q4_contexts = {}
        
        # default fields that are parsed from XBRL file
        self.us_gaap_tag_names_list = ['EarningsPerShareDiluted', 'EarningsPerShareBasic', 'GrossProfit', 'NetIncomeLoss', 'StockholdersEquity', 'CapitalExpenditure',
                                       'CashFlowFromOperations', 'Revenues', 'CostOfGoodsAndServicesSold', 'SellingGeneralAndAdministrativeExpense', 'ResearchAndDevelopmentExpense',
                                       'DepreciationDepletionAndAmortization', 'OperatingIncomeLoss', 'LongTermDebtNoncurrent'
                                       'WeightedAverageNumberOfDilutedSharesOutstanding', 'WeightedAverageNumberOfSharesOutstandingBasic']
        self.alternative_tag_names = {'Revenues': 'SalesRevenueNet',
                                      'CashFlowFromOperations': 'NetCashProvidedByUsedInOperatingActivities',
                                      'CapitalExpenditure': 'PaymentsToAcquirePropertyPlantAndEquipment'}

        # Add additional tags selected by user
        self.us_gaap_tag_names_list += extra_tags

        if xbrl_path is not None:
            with open(xbrl_path, 'r') as fh:
                self.raw_data = BeautifulSoup(fh, "lxml")

            for tag in self.raw_data.find_all():
                tag.name = tag.name.lower()

            self._define_relevant_contexts()
            self._parse_xbrl()
            self.data_df = pd.DataFrame(self.data)

    def __str__(self):
        return str(self.data)

    def _define_relevant_contexts(self):
        all_context_tags = self.raw_data.find_all(
            name=re.compile("context", re.IGNORECASE | re.MULTILINE))
        YTD_contexts = {}
        Q4_contexts = {}
        for tag in all_context_tags:
            for inner_tag in tag.find_all():
                name = inner_tag.name
                if ':' in name:
                    name = name.split(':')[-1]
                inner_tag.name = name.lower()
            startdate = tag.find('startdate')
            enddate = tag.find('enddate')
            period = tag.find(re.compile('period'))
            if startdate is not None:
                startdate = re.sub("[^0-9]", "", startdate.text)
                enddate = re.sub("[^0-9]", "", enddate.text)
                tdelta = datetime.strptime(
                    enddate, "%Y%m%d") - datetime.strptime(startdate, "%Y%m%d")
                if tdelta.days > 360 and "us-gaap" not in tag.attrs['id']:
                    if int(enddate[4:6]) > 6:
                        year = int(enddate[:4])
                    else:
                        year = int(startdate[:4])
                    # take the shortest context ID as the main YTD context
                    if year not in YTD_contexts.keys():
                        YTD_contexts[year] = tag.attrs['id']
                    else:
                        if len(tag.attrs['id']) < len(YTD_contexts[year]):
                            YTD_contexts[year] = tag.attrs['id']

            if period.instant is not None:
                date = re.sub("[^0-9]", "", period.instant.text)
                if int(date[4:6]) >= 8:  # suspected to be the 4th qurter
                    year = int(date[:4])
                    if year not in Q4_contexts.keys():
                        Q4_contexts[year] = tag.attrs['id']
                    else:
                        if len(tag.attrs['id']) < len(Q4_contexts[year]):
                            Q4_contexts[year] = tag.attrs['id']

        # flip the keys and values for later use
        for year in YTD_contexts.keys():
            self.YTD_contexts[YTD_contexts[year]] = year
        for year in Q4_contexts.keys():
            self.Q4_contexts[Q4_contexts[year]] = year

        # print(self.YTD_contexts)
        # print(self.Q4_contexts)

    def _find_us_gaap_tags(self, tag_name):
        tag_name = tag_name.lower()
        if len(tag_name) > 8:
            if tag_name[:8] != "us-gaap:":
                tag_name = "us-gaap:" + tag_name
        else:
            tag_name = "us-gaap:" + tag_name
        return self.raw_data.find_all(tag_name)

    def find_YTD_data(self, tag_name, allow_last_q_data=True):
        if tag_name not in self.data.keys():
            self.data[tag_name] = {}
        tags = self._find_us_gaap_tags(tag_name)
        found = False
        for tag in tags:
            context = tag.attrs['contextref']
            if context in self.YTD_contexts.keys():
                year = self.YTD_contexts[context]
                self.data[tag_name][year] = float(tag.text)
                found = True

        if not found and allow_last_q_data:
            for tag in tags:
                context = tag.attrs['contextref']
                if allow_last_q_data and context in self.Q4_contexts.keys():
                    year = self.Q4_contexts[context]
                    self.data[tag_name][year] = float(tag.text)
                    found = True

        if not found and tag_name in self.alternative_tag_names.keys():
            alt_tag_name = self.alternative_tag_names[tag_name].lower()
            alt_tag_name = "us-gaap:" + alt_tag_name
            tags = self._find_us_gaap_tags(alt_tag_name)
            for tag in tags:
                context = tag.attrs['contextref']
                if context in self.YTD_contexts.keys():
                    year = self.YTD_contexts[context]
                    self.data[tag_name][year] = float(tag.text)
                    found = True

    def _parse_xbrl(self):
        '''
        parse the xml and find data of all the predefined field names
        '''
        for tag_name in self.us_gaap_tag_names_list:
            self.find_YTD_data(tag_name)

    def add_additional_xbrl_file(self, xbrl_path):
        '''
        will update the data summary and dataframe
        notice that self.raw_data will get overwritten
        '''
        with open(xbrl_path, 'r') as fh:
            self.raw_data = BeautifulSoup(fh, "lxml")

        for tag in self.raw_data.find_all():
            tag.name = tag.name.lower()

        self._parse_xbrl()
        self.data_df = pd.DataFrame(self.data)

    def get_data(self):
        return self.data

    def get_data_df(self):
        return self.data_df
