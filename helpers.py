import csv
import urllib.request

from flask import redirect, render_template, request, session, url_for
from functools import wraps

def apology(top="", bottom=""):
    def escape(s):
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
            ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=escape(top), bottom=escape(bottom))


def apology1(top="", bottom=""):
    def escape(s):
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
            ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology1.html", top=escape(top), bottom=escape(bottom))


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


#http://download.finance.yahoo.com/d/quotes.csv?s=YHOO,GOOG,AAPL&f=sl1d1t1c1ohgv&e=.csv&columns='symbol,price,date,time,change,col1,high,low,col2
def lookup(symbol):
    if symbol.startswith("^"):
        return None

    if "," in symbol:
        return None

    try:
        url = "http://download.finance.yahoo.com/d/quotes.csv?&e=.csv&columns=symbol,price,change,col1,high,low,col2&f=sl1d1t1c1ohgv&s={}".format(symbol)
        print(url)
        webpage = urllib.request.urlopen(url)
        datareader = csv.reader(webpage.read().decode("utf-8").splitlines())
        row = next(datareader)
    except:
        print("xxxxx")
        return None

    # ensure stock exists
    #YHOO	46.485	0.255	46.41	46.55	46.24	651980
    try:
        symbol=row[0]
        price = float(row[1])
        change=(row[4])
        col1=(row[5])
        high=(row[6])
        low=(row[7])
        col2=(row[8])

    except:
        return None
    return {
        "name": row[0].upper(),
        "price": price,
        "symbol": row[0].upper(),
        "change":change,
        "col1":col1,
        "high": high,
        "low": low,
        "col2":col2

    }

def usd(value):
    return "${:,.2f}".format(value)
