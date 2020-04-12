# from lxml import etree
import re
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
from ipdb import set_trace

from config.xbrl_config import US_GAPP_TAGS_LIST, ALTERNATIVE_TAG_NAMES


class XBRL:

    def __init__(self, use_dei=False, extra_tags=[]):

        self.data = {}
        self.YTD_contexts = {}
        self.Q4_contexts = {}
        self.Q4_dates = set()
        self.latestQ_context = {}
        self.use_dei = use_dei

        # set some default contexts
        for year in range(2010, datetime.now().year+1):
            self.YTD_contexts['FD%dQ4YTD' % year] = year
            self.Q4_contexts['FI%dQ4' % year] = year
        # default fields that are parsed from XBRL file
        self.us_gaap_tag_names_list = US_GAPP_TAGS_LIST
        self.alternative_tag_names = ALTERNATIVE_TAG_NAMES

        # Add additional tags selected by user
        self.us_gaap_tag_names_list += extra_tags

    def __str__(self):
        return str(self.data)

    def _find_YTD_contexts(self):
        '''
        find contexts of YTD periods. usually the general contexts will have the shortest
        name string in every period. this is what we are looking for.
        '''
        all_context_tags = self.raw_data.find_all(
            name=re.compile("context", re.IGNORECASE | re.MULTILINE))
        YTD_contexts = {}
        for tag in all_context_tags:
            for inner_tag in tag.find_all():
                # cleaning the inner tags
                name = inner_tag.name
                if ':' in name:
                    name = name.split(':')[-1]
                inner_tag.name = name.lower()
            startdate = tag.find('startdate')
            enddate = tag.find('enddate')
            if startdate is not None:
                startdate = re.sub("[^0-9]", "", startdate.text)
                startdate = datetime.strptime(startdate, "%Y%m%d")
                enddate = re.sub("[^0-9]", "", enddate.text)
                enddate = datetime.strptime(enddate, "%Y%m%d")
                tdelta = enddate - startdate
                if tdelta.days > 360 and "us-gaap" not in tag.attrs['id']:
                    if self.use_dei and self.currentFY is not None:
                        if enddate.month == self.document_end_date.month and enddate.day == self.document_end_date.day:
                            delta_years = self.document_end_date.year - enddate.year
                            year = self.currentFY - delta_years
                        else:
                            continue
                    elif enddate.month >= 3:
                        # If we don't use DEI data we take a rule of thumb of common year-end months
                        year = enddate.year
                    else:
                        year = startdate.year
                    # take the shortest context ID as the main YTD context
                    if year not in YTD_contexts.keys():
                        YTD_contexts[year] = tag.attrs['id']
                    else:
                        if len(tag.attrs['id']) < len(YTD_contexts[year]):
                            YTD_contexts[year] = tag.attrs['id']
                    # the end date of the year might assist in finding the last quarter contexts later on
                    self.Q4_dates.add(enddate)
        # flip the keys and values for later use
        for year in YTD_contexts.keys():
            self.YTD_contexts[YTD_contexts[year]] = year

    def _find_endyearQ_contexts(self):
        '''
        Find context of end-of-year qurters contexts that represent the state at the end of the year
        '''
        all_context_tags = self.raw_data.find_all(
            name=re.compile("context", re.IGNORECASE | re.MULTILINE))
        Q4_contexts = {}
        Q4_dates_per_year = {}
        for tag in all_context_tags:
            for inner_tag in tag.find_all():
                 # cleaning the inner tags
                name = inner_tag.name
                if ':' in name:
                    name = name.split(':')[-1]
                inner_tag.name = name.lower()

            period = tag.find(re.compile('period'))
            if period.instant is not None:
                date = re.sub("[^0-9]", "", period.instant.text)
                date = datetime.strptime(date, '%Y%m%d')
                year = date.year
                month = date.month
                # looking for the latest quarter in each year, sometimes Q4 can end on 1st month of next year
                if month < 2:
                    year -= 1
                # year = str(year)
                if year not in Q4_dates_per_year.keys():
                    Q4_dates_per_year[year] = date
                    Q4_contexts[year] = tag.attrs['id']
                elif date in self.Q4_dates and len(tag.attrs['id']) <= len(Q4_contexts[year]):
                    Q4_dates_per_year[year] = date
                    Q4_contexts[year] = tag.attrs['id']
                elif date >= Q4_dates_per_year[year] and len(tag.attrs['id']) < len(Q4_contexts[year]):
                    Q4_dates_per_year[year] = date
                    Q4_contexts[year] = tag.attrs['id']

                # TODO - this is an ugly ugly workaround.... need to think of something better
                if 8 < len(tag.attrs['id']) * 2 < len(Q4_contexts[year]):
                    # sometimes there are context from a late date which are not meaningful
                    # they will usualy have a long id name
                    Q4_dates_per_year[year] = date
                    Q4_contexts[year] = tag.attrs['id']

        # flip the keys and values for later use
        for year in Q4_contexts.keys():
            self.Q4_contexts[Q4_contexts[year]] = year

    def _find_latestQ_context(self):
        '''
        Find context of end-of-year qurters contexts that represent the state at the end of the year
        '''
        all_context_tags = self.raw_data.find_all(
            name=re.compile("context", re.IGNORECASE | re.MULTILINE))
        # initialize the context name and date with unreasonable values
        latest_instant_context = 'a'*999
        latest_period_context = 'a'*999
        latest_instant_date = datetime.strptime('19481128', '%Y%m%d')
        latest_enddate = datetime.strptime('19481128', '%Y%m%d')
        for tag in all_context_tags:
            for inner_tag in tag.find_all():
                 # cleaning the inner tags
                name = inner_tag.name
                if ':' in name:
                    name = name.split(':')[-1]
                inner_tag.name = name.lower()

            period = tag.find(re.compile('period'))
            startdate = tag.find('startdate')
            enddate = tag.find('enddate')

            if period.instant is not None:
                date = re.sub("[^0-9]", "", period.instant.text)
                current_date = datetime.strptime(date, '%Y%m%d')
                # set_trace()
                if current_date >= latest_instant_date:
                    if len(tag.attrs['id']) <= len(latest_instant_context) or current_date > latest_instant_date:
                        latest_instant_context = tag.attrs['id']
                        latest_instant_date = current_date
                        continue

                # TODO - this is an ugly ugly workaround.... need to think of something better
                if 8 < len(tag.attrs['id']) * 2 < len(latest_instant_context):
                    # sometimes there are context from a late date which are not meaningful
                    # they will usualy have a long id name
                    latest_instant_context = tag.attrs['id']
                    latest_instant_date = current_date
                    continue

            if startdate is not None:
                startdate = datetime.strptime(
                    re.sub("[^0-9]", "", startdate.text), '%Y%m%d')
                enddate = datetime.strptime(
                    re.sub("[^0-9]", "", enddate.text), '%Y%m%d')
                tdelta = enddate - startdate

                if 35 < tdelta.days < 100 and enddate > latest_enddate:
                    if len(tag.attrs['id']) <= len(latest_period_context):
                        latest_period_context = tag.attrs['id']
                        latest_enddate = enddate

        date = max(latest_enddate, latest_instant_date).strftime("%d/%m/%Y")
        self.latestQ_context = {
            latest_instant_context: date, latest_period_context: date}

    def _find_us_gaap_tags(self, tag_name):
        tag_name = tag_name.lower()
        if len(tag_name) > 8:
            if tag_name[:8] != "us-gaap:":
                tag_name = "us-gaap:" + tag_name
        else:
            tag_name = "us-gaap:" + tag_name
        return self.raw_data.find_all(tag_name)

    def _find_YTD_data(self, tag_name, allow_Q4_data=True):
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

        if not found and tag_name in self.alternative_tag_names.keys():
            alt_tag_names = self.alternative_tag_names[tag_name]
            if type(alt_tag_names) is not list:
                alt_tag_names = [alt_tag_names]
            for alt_tag_name in alt_tag_names:
                alt_tag_name = "us-gaap:" + alt_tag_name.lower()
                alt_tags = self._find_us_gaap_tags(alt_tag_name)
                for tag in alt_tags:
                    context = tag.attrs['contextref']
                    if context in self.YTD_contexts.keys():
                        year = self.YTD_contexts[context]
                        self.data[tag_name][year] = float(tag.text)
                        found = True

        if not found and allow_Q4_data:
            for tag in tags:
                context = tag.attrs['contextref']
                if context in self.Q4_contexts.keys():
                    year = self.Q4_contexts[context]
                    self.data[tag_name][year] = float(tag.text)
                    found = True

        # TO DO - this copied block of code is not very elegant, need to think of a different approach
        if not found and allow_Q4_data and tag_name in self.alternative_tag_names.keys():
            alt_tag_names = self.alternative_tag_names[tag_name]
            if type(alt_tag_names) is not list:
                alt_tag_names = [alt_tag_names]
            for alt_tag_name in alt_tag_names:
                alt_tag_name = "us-gaap:" + alt_tag_name.lower()
                alt_tags = self._find_us_gaap_tags(alt_tag_name)
                for tag in alt_tags:
                    context = tag.attrs['contextref']
                    if context in self.Q4_contexts.keys():
                        year = self.Q4_contexts[context]
                        self.data[tag_name][year] = float(tag.text)
                        found = True

    def _find_latest_Q_data(self, tag_name):
        if tag_name not in self.data.keys():
            self.data[tag_name] = {}
        tags = self._find_us_gaap_tags(tag_name)
        found = False
        for tag in tags:
            context = tag.attrs['contextref']
            if context in self.latestQ_context.keys():
                date = self.latestQ_context[context]
                self.data[tag_name][date] = float(tag.text)
                found = True

        if not found and tag_name in self.alternative_tag_names.keys():
            alt_tag_names = self.alternative_tag_names[tag_name]
            if type(alt_tag_names) is not list:
                alt_tag_names = [alt_tag_names]
            for alt_tag_name in alt_tag_names:
                alt_tag_name = "us-gaap:" + alt_tag_name.lower()
                tags = self._find_us_gaap_tags(alt_tag_name)
                for tag in tags:
                    context = tag.attrs['contextref']
                    if context in self.latestQ_context.keys():
                        date = self.latestQ_context[context]
                        self.data[tag_name][date] = float(tag.text)
                        found = True

    def find_dei_info(self):
        # tags = self.raw_data.find_all('dei:CurrentFiscalYearEndDate'.lower())
        # self.year_end_date = tags[0].text
        # self.year_end_date = datetime.strptime(self.year_end_date, '--%m-%d')
        self.document_end_date = None
        self.currentFY = None
        self.latest_stock_count = None
        try:
            tags = self.raw_data.find_all('dei:DocumentPeriodEndDate'.lower())
            self.document_end_date = tags[0].text
            self.document_end_date = datetime.strptime(
                self.document_end_date, '%Y-%m-%d')

            tags = self.raw_data.find_all(
                'dei:DocumentFiscalYearFocus'.lower())
            self.currentFY = int(tags[0].text)
            context_ref = tags[0].attrs['contextref']
            self.YTD_contexts[context_ref] = self.currentFY
        except:
            pass

        try:
            tags = self.raw_data.find_all(
                'dei:EntityCommonStockSharesOutstanding'.lower())
            self.latest_stock_count = 0
            for tag in tags:
                self.latest_stock_count += int(tag.text)
        except:
            pass

    def _parse_YTD_xbrl(self):
        '''
        parse the xml and find data of all the predefined field in YTD contexts
        '''
        if self.use_dei:
            self.find_dei_info()
        self._find_YTD_contexts()
        self._find_endyearQ_contexts()
        for tag_name in self.us_gaap_tag_names_list:
            self._find_YTD_data(tag_name)

    def _parse_quarterly_xbrl(self):
        '''
        parse the xml and find data of all the predefined field in YTD contexts
        '''
        self._find_latestQ_context()
        for tag_name in self.us_gaap_tag_names_list:
            self._find_latest_Q_data(tag_name)

    def load_YTD_xbrl_file(self, xbrl_path):
        '''
        parse and load yearly reports (10-K or 20-F)
        will update the data summary and dataframe
        can add additional file on top of existing one, but notice that self.raw_data will get overwritten
        '''
        with open(xbrl_path, 'r') as fh:
            self.raw_data = BeautifulSoup(fh, "lxml")

        for tag in self.raw_data.find_all():
            tag.name = tag.name.lower()

        self._parse_YTD_xbrl()
        if self.use_dei and self.currentFY not in self.data['NumberOfShares'].keys() and self.currentFY is not None:
            self.data['NumberOfShares'][self.currentFY] = self.latest_stock_count
        self.data_df = pd.DataFrame(self.data)

    def load_10Q_xbrl_file(self, xbrl_path):
        '''
        parse and load quartely reports (10-Q), takes info of the last qurter described in the report
        will update the data summary and dataframe
        can add additional file on top of existing one, but notice that self.raw_data will get overwritten
        '''
        with open(xbrl_path, 'r') as fh:
            self.raw_data = BeautifulSoup(fh, "lxml")

        for tag in self.raw_data.find_all():
            tag.name = tag.name.lower()

        self._parse_quarterly_xbrl()
        self.data_df = pd.DataFrame(self.data)

    def get_data(self):
        return self.data

    def get_data_df(self):
        return self.data_df
