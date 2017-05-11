import os
import sqlite3
import re
import time

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.hash import sha256_crypt
from tempfile import gettempdir

from helpers import *

app = Flask(__name__)

if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

app.jinja_env.filters["usd"] = usd

app.config["SESSION_FILE_DIR"] = gettempdir()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

file = "finance.db"
db = sqlite3.connect(file, check_same_thread=False)
c = db.cursor()

#user_id  INTEGER,symbol text,price 
user_symbol_price_dict={}
def get_all_info():
    temp_dict={}
    alarm_items= c.execute("SELECT user_id,symbol,price FROM alarm_info").fetchall()
    for alarm_item in alarm_items:
        user_id=alarm_item[0]
        symbol=alarm_item[1]
        price=alarm_item[2]
        user_symbol_price_dict[str(user_id)+"\t"+symbol]=float(price)



def history():
    temp_dict={}
    transactions = c.execute("SELECT * FROM transactions").fetchall()
    for transaction in transactions:
        symbol=transaction[2]
        temp_dict[symbol]=symbol


    for symbol in temp_dict:
        time.sleep(5)
        price_dict=lookup(symbol)
        if price_dict is None:
           continue;
        symbol=price_dict["symbol"]     
        name=price_dict["name"]
        price=price_dict["price"]

        low=price_dict["low"]

        high=price_dict["high"]
        price=price_dict["price"]

        col2=price_dict["col2"]

        now = time.strftime("%s") 


        ##轮训并且报警       
        for key in user_symbol_price_dict:
            temp_user_id=key.split("\t")[0]
            temp_symbol=key.split("\t")[1]
            if  symbol==temp_symbol:
                if float(price)>user_symbol_price_dict[key]:
                   c.execute("UPDATE alarm_info set alarm='ALARM' where user_id=? and symbol=?",[temp_user_id,temp_symbol])
                   db.commit()
                   user=c.execute("SELECT email from users where id=?",[temp_user_id]).fetchall()[0]
                   if len(user)>0:
                      email=user[0]
                      if (email is not None) or (email!=""):
                         print("xxxxxxxxxxx")
                         redirect("http://47.91.40.70:8088/send_email?email="+email)
                         print("yyyyyyyyyyyy")
                else:
                   c.execute("UPDATE alarm_info set alarm='NO_ALARM' where user_id=? and symbol=?",[temp_user_id,temp_symbol])
                   db.commit()

        if not os.path.exists("static/"+symbol+".csv"):
           f=open("static/"+symbol+".csv",'w')
           print("Timestamp,close,high,low,open,volume",file=f, flush=True)
        else:
           f=open("static/"+symbol+".csv",'a+')
           print(now+","+str(price)+","+str(price)+","+str(high)+","+str(low)+","+str(col2),file=f, flush=True)
      

        #{'symbol': 'IWV', 'name': 'iShares Russell 3000 ETF', 'price': 139.59}


if __name__ == "__main__":
   get_all_info()
   history()
