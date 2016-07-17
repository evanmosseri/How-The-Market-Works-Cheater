import requests
import random
import math
import mechanize
import cookielib
from pyquery import PyQuery as pq
import time
import re
from datetime import datetime
import numpy as np
import itertools

__cookies__ = {'incap_ses_240_402322': 'trkeXFKxVzoJ+kjAHqdUA+kndlUAAAAA9x4JQslwTZzE4Vgrl4JPZQ==', 'YourVisitID': 'bb3fu5t7tl2gs131d4pv3casa1', 'e927ad4b5ab576572288d37acc14a42b':
               '136990abe0dbf91e4e69efd5247230fc', 'login_email': 'evan.mosseri%40gmail.com', 'visid_incap_402322': 'QR1s2ov6RdSfkIAVrm21/ekndlUAAAAAQUIPAAAAAABAN7Qn0gNloijni+3+7H/y'}
old_cookies = __cookies__

trade_url = "http://www.howthemarketworks.com/trading/trade.php"


def sign_in(username, password):
    base_url = "http://www.howthemarketworks.com/trading/index.php"
    br = mechanize.Browser()
    cj = cookielib.LWPCookieJar()
    br.set_cookiejar(cj)
    br.set_handle_robots(False)
    br.addheaders = [('User-agent', 'Firefox')]
    br.open(base_url)
    login_form = [frm for frm in br.forms() if frm.attrs.get('name') == "form1"][
        0]
    login_form["user_email"] = username
    login_form["user_pw"] = password
    c = br.select_form(name='form1')
    br.submit()
    cookies = requests.utils.dict_from_cookiejar(cj)
    global __cookies__
    __cookies__ = cookies
    return cookies


def make_transaction(transaction_type, ticker, quantity):
    data = dict(confirmed="true", submitted="True", random_trade_id=random.randint(100000, 999999), numsharesfield=quantity,
                symbolfield=ticker, radiobuttonbuyshort=transaction_type, targetsym="sym", ordertypelist=1, expirationmarketlist=20)
    req = requests.post(trade_url, cookies=__cookies__, data=data)


def get_system_price(ticker):
    return float(pq(requests.get("http://www.howthemarketworks.com/trading/account.php", cookies=__cookies__).content)("a:contains('{}')".format(ticker)).parent().parent().children("td").eq(3).text())


def get_availble_funds():
    return float(pq(requests.get("http://www.howthemarketworks.com/trading/account.php", cookies=__cookies__).content)("td[width=\"80\"].accountTableShort div").text().replace("$", "").replace(",", ""))


def get_hmw_price(ticker):
    c = pq(requests.post("http://www.howthemarketworks.com/trading/trade.php", data=dict(numsharesfield=10, symbolfield=ticker, radiobuttonbuyshort="buy", submitted="TRUE",
                                                                                         targetURL="http://www.howthemarketworks.com/trading/stock-quotes.php", targetsym="sym", ordertypelist=1, expirationmarketlist=20), cookies=__cookies__).content)
    return float(re.findall(r'\d{1,3}\.\d{1,2}', re.findall(r'Real-time quote.*\$\d{1,3}\.\d{1,2}', c(".notice").text())[0])[0])


def get_google_price(ticker):
    url = "https://www.google.com/finance?q={}".format(ticker)
    p = pq(url)
    return {"price": float(p(".id-price-panel.goog-inline-block .pr").text())}


def max_shares(ticker):
    return int((.99 * get_availble_funds()) / get_google_price(ticker)["price"])


def get_mean_stock_price(ticker):
    prices = []
    for i in range(3):
        prices.append(get_google_price(ticker)["price"])
        time.sleep(2)
    return [np.mean(prices), prices[-1], get_hmw_price(ticker)]


def profit(num_shares, goog, hmw, trans="buy", fee=10):
    ans = (num_shares * (goog - hmw)) - \
        fee if trans == "buy" else (num_shares * (hmw - goog)) - fee
    return ans


if __name__ == "__main__" and datetime.now().hour >= 9 and datetime.now().hour < 16:
    sign_in("emosseri@utexas.edu", "OMMITED")
    stocks = ["GPRO", "YHOO", "AMBA", "BABA", "TSLA", "AAPL", "NVDA", "YELP"]
    frequency = 1
    stocks = list(itertools.chain(
        *[("{} ".format(x) * frequency).split(" ")[0:-1] for x in stocks]))
    last_time = None
    cycle = 0
    min_profit = 100
    fee = 10
    timeout = 180
    while True:
        stock = stocks[cycle % (len(stocks))]
        cycle += 1
        time.sleep(1)
        last_time = time.time()
        print "getting mean stock price for {}\n\n".format(stock)
        c = get_mean_stock_price(stock)
        print "Stock Prices: Google:[mean: {} last: {}] HMW: {}".format(c[0], c[1], c[2])
        shares = max_shares(stock)

        print "Buy Condition: {} {}".format(profit(shares, c[0], c[2], fee=fee), profit(shares, c[1], c[2], fee=fee))
        print "Short Condition: {} {}".format(profit(shares * 2, c[0], c[2], fee=fee, trans="short"), profit(shares * 2, c[1], c[2], fee=fee, trans="short"))
        if (profit(shares, c[0], c[2], fee=fee) > min_profit) and (profit(shares, c[1], c[2], fee=fee) > min_profit):
            print "Upside: {}".format(profit(shares, c[1], c[2], fee=fee))
            make_transaction("buy", stock, shares)
            print "buying {}".format(stock)
            last_time = time.time()
            while True:
                try:
                    n = get_hmw_price(stock)
                except:
                    print "n is invalid, breaking"
                    time.sleep(3)
                    make_transaction("sell", stock, shares)
                    break
                goog_price = get_google_price(stock)["price"]
                print "Current Price: {}, Projected Price: {}, Google Price: {}".format(n, c[1], goog_price)
                if n >= goog_price:
                    time.sleep(3)
                    make_transaction("sell", stock, shares)
                    print "selling {} at {}".format(stock, n)
                    break
                elif n < (c[2] - .01):
                    time.sleep(3)
                    make_transaction("sell", stock, shares)
                    print "sell {} at {} due to unprojected decrease".format(stock, n)
                    break
                elif goog_price < (c[1] - .01):
                    cycle -= 1
                    time.sleep(3)
                    make_transaction("sell", stock, shares)
                elif (time.time() - last_time > timeout):
                    print "Time Ran Out!!!"
                    time.sleep(3)
                    make_transaction("sell", stock, shares)
                    break
        elif (profit(shares * 2, c[0], c[2], fee=fee, trans="short") > min_profit) and (profit(shares * 2, c[1], c[2], fee=fee, trans="short") > min_profit):
            print "Upside: {}".format(profit(shares * 2, c[0], c[2], fee=fee, trans="short"))
            make_transaction("short", stock, shares * 2)
            print "shorting {}".format(stock)
            last_time = time.time()
            while True:
                try:
                    n = get_hmw_price(stock)
                except:
                    print "n is invalid, breaking"
                    time.sleep(3)
                    make_transaction("cover", stock, shares * 2)
                    break
                goog_price = get_google_price(stock)["price"]
                print "Current Price: {}, Projected Price: {}, Google Price: {}".format(n, c[1], goog_price)
                if n <= goog_price:
                    time.sleep(3)
                    make_transaction("cover", stock, shares * 2)
                    print "covering {} at {}".format(stock, n)
                    break
                elif n > (c[2] + .01):
                    time.sleep(3)
                    make_transaction("cover", stock, shares * 2)
                    print "covering {} at {} due to unprojected increase".format(stock, n)
                    break
                elif goog_price > (c[1] + .01):
                    time.sleep(3)
                    make_transaction("cover", stock, shares * 2)
                elif (time.time() - last_time > timeout):
                    print "Time Ran Out!!!"
                    time.sleep(3)
                    make_transaction("cover", stock, shares * 2)
                    break
        print "%.2fs" % (time.time() - last_time)
