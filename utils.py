import edgar
import re
import requests

# company = edgar.Company("Oracle Corp", "0001341439")
# cik = edgar.getCIKFromCompany()
# tree = company.getAllFilings(filingType="10-K")
# docs = edgar.getDocuments(tree, noOfDocuments=5)
# for j in range(len(docs)):
#     path = "./SEC-Edgar-data/" + str(j)
#     with open(path, "wb") as f:
#         f.write(docs[j].encode('ascii', 'ignore'))


def save_documents_to_folder(company, cik, type="10-K", path='./SEC-Edgar-data/', number_of_documents=5):
    pass


def get_cik_from_ticker(ticker):
    URL = 'http://www.sec.gov/cgi-bin/browse-edgar?CIK={}&Find=Search&owner=exclude&action=getcompany'
    CIK_RE = re.compile(r'.*CIK=(\d{10}).*')
    results = CIK_RE.findall(get(URL.format(ticker)).content)
    if len(results):
        return str(results)
    else:
        print('could not find it...')
        return None


def get_name_from_ticker(ticker):
    url = "http://d.yimg.com/autoc.finance.yahoo.com/autoc?query={}&region=1&lang=en".format(
        ticker)

    result = requests.get(url).json()

    for x in result['ResultSet']['Result']:
        if x['symbol'] == ticker:
            return x['name']


company = get_name_from_ticker("MSFT")

print(company)
