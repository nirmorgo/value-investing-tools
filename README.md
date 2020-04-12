# Value-Investing-Tools
playing around with stock valuation techniques

## Main Functionalities
* SEC-Edgar Crawler - scans sec.gov for financial reports and downloads all of them on your local machine. Can be set to download either the full text of the report or the big ugly XBRL file
* XBRL Parser - can load a big ugly XBRL file (or a number of them) and turn it into a nice Pandas DataFrame
* Valuation functions - all sorts of valuation functions based on all sorts of fundumental data
* Stock Analyzer - kind of a demo script. Uses all of the above tools in order to analyze a certain stock

## Setup
* You will need a Simfin API key if you want to get anything which is related to the stock price. you can get one at https://simfin.com. once you have it you should add it in

        config/config.py

* Install the packages listed in the requirements file and your good to go

        pip3 install -r requirements.txt

## Usage example
In order to analyze a certain stock, run the following script with a certain TICKER (like FB or AMZN) from the project folder

    python3 ./stock_analysis.py --ticker=<TICKER> -d


Cheers!