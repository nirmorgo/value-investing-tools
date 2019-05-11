# from lxml import etree
import re
from bs4 import BeautifulSoup
from ipdb import set_trace
import pandas as pd


class XBRL:

    def __init__(self, xbrl_path, extra_tags=[]):
        
        with open(xbrl_path, 'r') as fh:
            self.raw_data = BeautifulSoup(fh, "lxml")
        
        for tag in self.raw_data.find_all():
            tag.name = tag.name.lower()

        self.data = {}
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

        self.ytd4_finder = re.compile('FD[0-9]+Q4YTD$')
        self.q4_finder = re.compile('FI[0-9]+Q4$')

        self._parse_xbrl()
        self.data_df = pd.DataFrame(self.data)

    def __str__(self):
        return str(self.data)

    def _find_us_gaap_tags(self, tag_name):
        tag_name = tag_name.lower()
        if len(tag_name) > 8:
            if tag_name[:8] != "us-gaap:":
                tag_name = "us-gaap:" + tag_name
        else:
            tag_name = "us-gaap:" + tag_name
        # print(tag_name)
        return self.raw_data.find_all(tag_name)

    def find_YTD_data(self, tag_name, allow_last_q_data=True):
        if tag_name not in self.data.keys():
            self.data[tag_name] = {}
        tags = self._find_us_gaap_tags(tag_name)
        found = False
        for tag in tags:
            context = tag.attrs['contextref']
            if self.ytd4_finder.match(context):
                year = context[2:6]
                self.data[tag_name][year] = float(tag.text)
                found = True

        if not found and allow_last_q_data:
            for tag in tags:
                context = tag.attrs['contextref']
                if allow_last_q_data and self.q4_finder.match(context):
                    year = context[2:6]
                    self.data[tag_name][year] = float(tag.text)
                    found = True

        if not found and tag_name in self.alternative_tag_names.keys():
            alt_tag_name = self.alternative_tag_names[tag_name].lower()
            alt_tag_name = "us-gaap:" + alt_tag_name
            tags = self._find_us_gaap_tags(alt_tag_name)
            for tag in tags:
                context = tag.attrs['contextref']
                if allow_last_q_data and self.ytd4_finder.match(context):
                    year = context[2:6]
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
        

       