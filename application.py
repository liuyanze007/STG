import sqlite3
import re
import time

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.hash import sha256_crypt
from tempfile import gettempdir

from helpers import *

from flask import jsonify



from flask_mail import Mail, Message


#app = Flask(__name__, static_folder='', static_url_path='')

app = Flask(__name__,static_folder='static', static_url_path='')




app.config.update(   
     MAIL_SERVER='smtp.qq.com',   
     MAIL_PORT=465,  
     MAIL_USE_SSL=True,  
     MAIL_USERNAME ='747552283',  
     MAIL_PASSWORD ='yzsolzqpodasbaij'    
)

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


code_dict={}
fullname_dict={}
symbol_file=open("symbol.dict","r")
for line in symbol_file.readlines():
    line_list=line.split("\t")
    code=line_list[0]
    symbol=line_list[1]
    fullname=line_list[2]
    code_dict[symbol]=code
    fullname_dict[symbol]=fullname



mail = Mail(app)
@app.route("/send_email")
def send_email():   
    email_string=request.args.get("email")
    msg = Message(subject="ALARM!!!!!", sender='747552283@qq.com', recipients=[email_string])    
    msg.html = "ALARM!!!!!!!!!!"   
    mail.send(msg)   



@app.route("/index")
@login_required
def index():
    current_user = session["user_id"]
    temp_message_list = c.execute("SELECT id,from_id,to_id,title,message,time,read_flag FROM message_info where to_id = ?",[current_user]).fetchall()
    db.commit()
    all_message_count=len(temp_message_list);
    unread_message_list = c.execute("SELECT id,from_id,to_id,title,message,time,read_flag FROM message_info where to_id = ? and read_flag=0",[current_user]).fetchall()
    db.commit()
    unread_message_count=len(unread_message_list);
 
    current_cash = c.execute("SELECT cash FROM users WHERE id = :CURRENT_USER", [current_user]).fetchall()[0][0]
    available = c.execute("SELECT symbol, sum(quantity) FROM transactions WHERE user_id = :user_id GROUP BY symbol",
                          [session["user_id"]]).fetchall()
    stocks_value = 0
    for stock in available:
        stocks_value += (stock[1] * lookup(stock[0])["price"])
    c.execute("UPDATE users SET assets = :assets WHERE id = :user_id", [stocks_value, current_user])
    db.commit()
    return render_template("index.html", current_cash=current_cash, available=available, lookup=lookup, usd=usd, stocks_value=stocks_value,all_message_count=all_message_count,unread_message_count=unread_message_count)




@app.route("/current")
@login_required
def current():
    current_user = session["user_id"]
    temp_message_list = c.execute("SELECT id,from_id,to_id,title,message,time,read_flag FROM message_info where to_id = ?",[current_user]).fetchall()
    db.commit()
    all_message_count=len(temp_message_list);

    unread_message_list = c.execute("SELECT id,from_id,to_id,title,message,time,read_flag FROM message_info where to_id = ? and read_flag=0",[current_user]).fetchall()
    db.commit()

    unread_message_count=len(unread_message_list);
 
    current_cash = c.execute("SELECT cash FROM users WHERE id = :CURRENT_USER", [current_user]).fetchall()[0][0]
    available = c.execute("SELECT symbol, sum(quantity) FROM transactions WHERE user_id = :user_id GROUP BY symbol",
                          [session["user_id"]]).fetchall()
    stocks_value = 0
    for stock in available:
        stocks_value += (stock[1] * lookup(stock[0])["price"])
    c.execute("UPDATE users SET assets = :assets WHERE id = :user_id", [stocks_value, current_user])
    db.commit()
    return render_template("current.html", current_cash=current_cash, available=available, lookup=lookup, usd=usd, stocks_value=stocks_value,all_message_count=all_message_count,unread_message_count=unread_message_count)



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    current_user = session["user_id"]
    current_cash = c.execute("SELECT cash FROM users WHERE id = :CURRENT_USER", [current_user]).fetchall()[0][0]
    """Buy shares of stock."""
    if request.method == "GET":
        return render_template("buy.html", current_cash=usd(current_cash))
    elif request.method == "POST":
        now = time.strftime("%c")
        stock_symbol = request.form.get("stock-symbol")
        try:
            stock_quantity = int(request.form.get("stock-quantity"))
        except ValueError:
            return apology("ERROR", "ENTER QUANTITY IN WHOLE NUMBERS ONLY")

        if not stock_symbol:
            return apology("ERROR", "FORGOT STOCK SYMBOL")
        elif not stock_quantity:
            return apology("ERROR", "FORGOT DESIRED QUANTITY")

        stock_info = lookup(stock_symbol)
        if not stock_info:
            return apology("ERROR", "INVALID STOCK")
        transaction_cost = stock_info["price"] * stock_quantity
        if transaction_cost <= current_cash:
            current_cash -= transaction_cost
            c.execute("UPDATE users SET cash = :cash WHERE id = :id", [current_cash, current_user])
            c.execute("INSERT INTO transactions(user_id, symbol, price, quantity, transaction_date)"
                      "VALUES(:user_id, :symbol, :price, :quantity, :transaction_date)",
                      [current_user, stock_info["symbol"], stock_info["price"], stock_quantity, now])
            db.commit()
            print("Transaction sent.")
        else:
            return apology("ERROR", "INSUFFICIENT FUNDS")
        return redirect(url_for("index"))


@app.route("/history",methods=["GET", "POST"])
@login_required
def history():
    """Show history of transactions."""
    if request.method == "GET":
       current_user = session["user_id"]
       transactions = c.execute("SELECT * FROM transactions WHERE user_id = :user_id", [current_user]).fetchall()
       return render_template("history.html", transactions=transactions, lookup=lookup, usd=usd)
    elif request.method == "POST":
       current_user = session["user_id"]
       Transaction_StartTime=request.form.get("Transaction_StartTime")
       Transaction_EndTime=request.form.get("Transaction_EndTime")
       transactions = c.execute("SELECT * FROM transactions WHERE user_id = :user_id", [current_user]).fetchall()
       temp_transactions=[]
       if Transaction_StartTime!="" and  Transaction_EndTime!="":
          starttime_stamp = time.mktime(time.strptime(Transaction_StartTime,"%m/%d/%Y"))               
          endtime_stamp = time.mktime(time.strptime(Transaction_EndTime,"%m/%d/%Y"))               
          for transaction in transactions:
              time_string=transaction[5]
              time_stamp = time.mktime(time.strptime(time_string,"%a %b %d %H:%M:%S %Y"))               
              if time_stamp>=starttime_stamp and time_stamp<=endtime_stamp:
                 temp_transactions.append(transaction) 
      
       elif Transaction_StartTime!="" and  Transaction_EndTime=="":
          starttime_stamp = time.mktime(time.strptime(Transaction_StartTime,"%m/%d/%Y"))               
          for transaction in transactions:
              time_string=transaction[5]
              time_stamp = time.mktime(time.strptime(time_string,"%a %b %d %H:%M:%S %Y"))               
              if time_stamp>=starttime_stamp:
                 temp_transactions.append(transaction) 

       elif Transaction_StartTime=="" and  Transaction_EndTime!="":
          endtime_stamp = time.mktime(time.strptime(Transaction_EndTime,"%m/%d/%Y"))               
          for transaction in transactions:
              time_string=transaction[5]
              time_stamp = time.mktime(time.strptime(time_string,"%a %b %d %H:%M:%S %Y"))               
              if time_stamp<=endtime_stamp:
                 temp_transactions.append(transaction) 
       elif Transaction_StartTime=="" and  Transaction_EndTime=="":
          for transaction in transactions:
              temp_transactions.append(transaction) 
       return render_template("history.html", transactions=temp_transactions, lookup=lookup, usd=usd)



@app.route("/history_others",methods=["GET", "POST"])
@login_required
def history_others():
    """Show history of transactions."""
    if request.method == "GET":

       current_user = session["user_id"]
       other_user=request.args.get("user_id")
       transactions = c.execute("SELECT * FROM transactions WHERE user_id = :user_id", [other_user]).fetchall()
       return render_template("history_others.html", transactions=transactions, lookup=lookup, usd=usd)
    elif request.method == "POST":

       current_user = session["user_id"]
       other_user=request.form.get("other_user")

       Transaction_StartTime=request.form.get("Transaction_StartTime")
       Transaction_EndTime=request.form.get("Transaction_EndTime")


       transactions = c.execute("SELECT * FROM transactions WHERE user_id = :user_id", [other_user]).fetchall()
       temp_transactions=[]
       if Transaction_StartTime!="" and  Transaction_EndTime!="":
          starttime_stamp = time.mktime(time.strptime(Transaction_StartTime,"%m/%d/%Y"))               
          endtime_stamp = time.mktime(time.strptime(Transaction_EndTime,"%m/%d/%Y"))               
          for transaction in transactions:
              time_string=transaction[5]
              time_stamp = time.mktime(time.strptime(time_string,"%a %b %d %H:%M:%S %Y"))               
              if time_stamp>=starttime_stamp and time_stamp<=endtime_stamp:
                 temp_transactions.append(transaction) 
      
       elif Transaction_StartTime!="" and  Transaction_EndTime=="":
          starttime_stamp = time.mktime(time.strptime(Transaction_StartTime,"%m/%d/%Y"))               
          for transaction in transactions:
              time_string=transaction[5]
              time_stamp = time.mktime(time.strptime(time_string,"%a %b %d %H:%M:%S %Y"))               
              if time_stamp>=starttime_stamp:
                 temp_transactions.append(transaction) 

       elif Transaction_StartTime=="" and  Transaction_EndTime!="":
          endtime_stamp = time.mktime(time.strptime(Transaction_EndTime,"%m/%d/%Y"))               
          for transaction in transactions:
              time_string=transaction[5]
              time_stamp = time.mktime(time.strptime(time_string,"%a %b %d %H:%M:%S %Y"))               
              if time_stamp<=endtime_stamp:
                 temp_transactions.append(transaction) 
       elif Transaction_StartTime=="" and  Transaction_EndTime=="":
          for transaction in transactions:
              temp_transactions.append(transaction) 
       return render_template("history_other.html", transactions=temp_transactions, lookup=lookup, usd=usd)



@app.route("/leaderboard")
@login_required
def leaderboard():

    leaders = c.execute("SELECT username, cash, assets,id,is_administrator FROM users ORDER BY cash + assets DESC").fetchall()

    current_user = session["user_id"]

    user=c.execute("SELECT username,is_administrator FROM users WHERE id = :user_id", [current_user]).fetchall()[0]

    print(user[1]);

    return render_template("leaderboard.html", leaders=leaders, usd=usd,current_username=user[0],current_userid=current_user,is_administrator=user[1])


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        c.execute("SELECT * FROM users WHERE username = :username", [request.form.get("username").lower()])
        all_rows = c.fetchall()

        # ensure username exists and password is correct
        if len(all_rows) != 1 or request.form.get("password")!=all_rows[0][2]:
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = all_rows[0][0]

        # redirect user to home page
        return redirect(url_for("index"))

    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")
    elif request.method == "POST":
        if not request.form.get("stock-symbol"):
            return apology("Error", "Forgot to enter a stock")

        print(request.form.get("stock-symbol"))

        stock = lookup(request.form.get("stock-symbol"))
        print(stock)
        if not stock:
            return apology("ERROR", "INVALID STOCK")
        return render_template("quoted.html", stock=stock)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
    username = request.form.get("username")
    password = request.form.get("password")
    password_confirm = request.form.get("password-confirm")
    fullname= request.form.get("fullname")
    email= request.form.get("email")
    facebooklink= request.form.get("facebooklink")
    phonenumber= request.form.get("phonenumber")

    # if get request return register template
    if request.method == "GET":
        return render_template("register.html")
    # if post request
    elif request.method == "POST":
        # check fields for completion
        if not request.form.get("username"):
            return apology("Error","Forgot Username")
        elif not request.form.get("password"):
            return apology("Error", "Forgot Password")
        elif not request.form.get("password-confirm"):
            return apology("Error", "Forgot Confirmation")

        # if passwords match
        if password == password_confirm:
            # encrypt password
            #hashed = sha256_crypt.encrypt(password)
            hashed = password
            username = re.sub(r'\W+', '', username.lower())
            try:
                # send user details to database
                c.execute("INSERT INTO users(username, hash,fullname,email,phonenumber,facebooklink) VALUES(:username, :hash,:fullname,:email,:phonenumber,:facebooklink)", [username, hashed,fullname,email,phonenumber,facebooklink])
                db.commit()

                # immediately log user in
                session["user_id"] = c.execute("SELECT * FROM users WHERE username = :username", [username]).fetchall()[0][0]

                # send user to index
                return redirect(url_for("index"))

            # if username is not unique alert user
            except sqlite3.IntegrityError:
                return apology("Error", "Username taken")
        else:
            return apology("Passwords don't match")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "GET":
        available = c.execute("SELECT symbol, sum(quantity) FROM transactions WHERE user_id = :user_id GROUP BY symbol", [session["user_id"]]).fetchall()
        return render_template("sell.html")
    elif request.method == "POST":
        now = time.strftime("%c")
        current_user = session["user_id"]
        stock_symbol = request.form.get("stock-symbol")
        current_cash = c.execute("SELECT cash FROM users WHERE id = :CURRENT_USER", [current_user]).fetchall()[0][0]
        stock_available = c.execute(
            "SELECT sum(quantity) FROM transactions WHERE user_id = :user_id AND symbol = :symbol",
            [current_user, stock_symbol]).fetchall()
        try:
            stock_quantity = int(request.form.get("stock-quantity"))
        except ValueError:
            return apology("ERROR", "ENTER QUANTITY IN WHOLE NUMBERS ONLY")

        if not stock_symbol:
            return apology("ERROR", "Missing stock symbol")
        if not stock_available[0][0]:
            return apology("ERROR", "You don't own this security")

        if stock_quantity <= stock_available[0][0]:
            print("transaction possible")
            stock_info = lookup(stock_symbol)
            if not stock_info:
                return apology("ERROR", "INVALID STOCK")
            current_cash += stock_info["price"] * stock_quantity
            c.execute("UPDATE users SET cash = :cash WHERE id = :id", [current_cash, current_user])
            c.execute("INSERT INTO transactions(user_id, symbol, price, quantity, transaction_date)"
                      "VALUES(:user_id, :symbol, :price, :quantity, :transaction_date)",
                      [current_user, stock_info["symbol"], stock_info["price"], 0 - stock_quantity, now])
            db.commit()
            print("Transaction sent.")
        else:
            return apology("ERROR", "You don't own that much!")
        return redirect(url_for("index"))



@app.route("/like", methods=["GET", "POST"])
def like():
    # if get request return register template
    if request.method == "GET":
        from_id= request.args.get("from_id")
        like_id= request.args.get("like_id")
        try:
           c.execute("INSERT INTO like_info(from_id,like_id) VALUES (?,?)", [from_id,like_id])
           db.commit()
           title="add_friend_message";
           message="click_this_to_accepted: "+" http://47.91.40.70:8088"+url_for("accept_like")+"?from_id="+from_id;
           return redirect(url_for("send_message")+"?title="+title+"&message="+message+"&from_id="+from_id+"&to_id="+like_id)
        #if username is not unique alert user
        except sqlite3.IntegrityError:
            return apology("Error", "Username taken")

    # if post request
    elif request.method == "POST":
        # check fields for completion
        if not request.form.get("from_id"):
            return apology("Error", "Forgot from_id")
        elif not request.form.get("like_id"):
            return apology("Error", "Forgot like_id")

        try:
            c.execute("INSERT INTO like_info(from_id,like_id) VALUES(:from_id, :like_id)", [from_id,like_id])
            db.commit()
            return redirect(url_for("index"))

        # if username is not unique alert user
        except sqlite3.IntegrityError:
            return apology("Error", "Username taken")




@app.route("/accept_like", methods=["GET", "POST"])
def accept_like():
    # if get request return register template
    if request.method == "GET":
        from_id= request.args.get("from_id")
        message_id= request.args.get("message_id")
        like_id= session["user_id"]
        try:

           c.execute("UPDATE message_info set read_flag=1 WHERE  id= ?", [message_id])
           db.commit()
 
           c.execute("UPDATE like_info set accepted_flag=1 where from_id=? and like_id=?", [from_id,like_id])
           db.commit()
           return redirect(url_for("friends_list"))
        except sqlite3.IntegrityError:
            return apology("Error", "Username taken")
    elif request.method == "POST":
        # check fields for completion
        if not request.form.get("from_id"):
            return apology("Error", "Forgot from_id")
        elif not request.form.get("like_id"):
            return apology("Error", "Forgot like_id")

        try:
            # send user details to database
            c.execute("INSERT INTO users_like(from_id,like_id) VALUES(:from_id, :like_id)", [from_id,like_id])
            db.commit()
            # send user to index
            return redirect(url_for("index"))

        # if username is not unique alert user
        except sqlite3.IntegrityError:
            return apology("Error", "Username taken")



@app.route("/reject_like", methods=["GET", "POST"])
def reject_like():
    # if get request return register template
    if request.method == "GET":
        from_id= request.args.get("from_id")
        message_id= request.args.get("message_id")
        like_id= session["user_id"]
        try:
           c.execute("UPDATE message_info set read_flag=1 WHERE  id= ?", [message_id])
           db.commit()
           return redirect(url_for("friends_list"))
        except sqlite3.IntegrityError:
           return apology("Error", "Username taken")
 
    elif request.method == "POST":
        # check fields for completion
        if not request.form.get("from_id"):
            return apology("Error", "Forgot from_id")
        elif not request.form.get("like_id"):
            return apology("Error", "Forgot like_id")
        try:
            return redirect(url_for("index"))
        except sqlite3.IntegrityError:
            return apology("Error", "Username taken")



@app.route("/send_message", methods=["GET", "POST"])
def send_message():
    if request.method == "GET":
        from_id= request.args.get("from_id")
        to_id= request.args.get("to_id")
        title=request.args.get("title")
        message=request.args.get("message")
        try:

           if title or message:
              timestamp=int(time.time())
              c.execute("INSERT INTO message_info(from_id,to_id,title,message,time,read_flag,type) VALUES(:from_id, :to_id,:title,:message,:time,:read_flag,:type)", [from_id,to_id,title,message,timestamp,0,1])
              db.commit()
              return redirect(url_for("message_list"))
           else:
              return render_template("send_message.html",from_id=from_id,to_id=to_id)
        #if username is not unique alert user
        except sqlite3.IntegrityError:
            return apology("Error", "Username taken")
    # if post request
    elif request.method == "POST":
        current_user = session["user_id"]
        from_id=request.form.get("from_id")
        to_id=request.form.get("to_id")

        title=request.form.get("title")
        message=request.form.get("message")

        if not request.form.get("title"):
            return apology("Error", "Forgot title")
        elif not request.form.get("message"):
            return apology("Error", "Forgot message")

        try:
            timestamp=int(time.time())
            c.execute("INSERT INTO message_info(from_id,to_id,title,message,time,read_flag) VALUES(:from_id, :to_id,:title,:message,:time,:read_flag)", [from_id,to_id,title,message,timestamp,0])
            db.commit()
            message_list=[]
            temp_message_list = c.execute("SELECT id,from_id,to_id,title,message,time,read_flag FROM message_info WHERE  to_id= ?", [current_user]).fetchall()
            if len(temp_message_list)>0:
               message_list = temp_message_list[0]

            return redirect(url_for("message_list"))

        except sqlite3.IntegrityError:
            return apology("Error", "Username taken")



@app.route("/reply_message", methods=["GET", "POST"])
def reply_message():
    if request.method == "GET":
        message_id= request.args.get("message_id")
        try:
           temp_message_list = c.execute("SELECT from_id,to_id,title,message FROM message_info WHERE  id= ?", [message_id]).fetchall()
           if len(temp_message_list)>0:
              from_id=temp_message_list[0][0] 
              to_id=temp_message_list[0][1] 
              title=temp_message_list[0][2] 
              message=temp_message_list[0][3] 
              title=" RELY TO : "+title
              message="\nRELY TO : "+message

           return render_template("reply_message.html",from_id=to_id,to_id=from_id,title1=title,message=message)
        except sqlite3.IntegrityError:
            return apology("Error", "Username taken")

    elif request.method == "POST":
        current_user = session["user_id"]
        from_id=request.form.get("from_id")
        to_id=request.form.get("to_id")

        title=request.form.get("title")
        message=request.form.get("message")

        if not request.form.get("title"):
            return apology("Error", "Forgot title")
        elif not request.form.get("message"):
            return apology("Error", "Forgot message")

        try:
            timestamp=int(time.time())
            c.execute("INSERT INTO message_info(from_id,to_id,title,message,time,read_flag) VALUES(:from_id, :to_id,:title,:message,:time,:read_flag)", [from_id,to_id,title,message,timestamp,0])
            db.commit()
            message_list=[]
            temp_message_list = c.execute("SELECT id,from_id,to_id,title,message,time,read_flag,type FROM message_info WHERE  to_id= ?", [current_user]).fetchall()
            if len(temp_message_list)>0:
               message_list = temp_message_list[0]
            return render_template("message_list.html",message_list=message_list)

        except sqlite3.IntegrityError:
            return apology("Error", "Username taken")








@app.route("/message", methods=["GET", "POST"])
def message():
    if request.method == "GET":
        message_id= request.args.get("message_id")
        try:
           c.execute("UPDATE message_info set read_flag=1 WHERE  id= ?", [message_id])
           db.commit()
           temp_message_list = c.execute("SELECT from_id,to_id,title,message,time,read_flag,type FROM message_info WHERE  id= ?", [message_id]).fetchall()
           db.commit()
           from_username="";
           to_username="";
           title="";
           message="";
           time1="";
           read_flag=1;

           if len(temp_message_list)>0:
              title=temp_message_list[0][2]               
              message=temp_message_list[0][3]
              time1=temp_message_list[0][4]

              read_flag=(temp_message_list[0][5])


              timeArray = time.localtime(int(time1))  
              time1= time.strftime("%Y-%m-%d %H:%M:%S", timeArray)  


              from_user_info= c.execute("SELECT  username FROM users WHERE id = :CURRENT_USER", [temp_message_list[0][0]]).fetchall()[0]
              from_username=from_user_info[0]

              to_user_info= c.execute("SELECT  username FROM users WHERE id = :CURRENT_USER", [temp_message_list[0][1]]).fetchall()[0]
              to_username=to_user_info[0]

           return render_template("message.html",from_username=from_username,to_username=to_username,title1=title,message=message,time1=time1,read_flag=read_flag)
        except sqlite3.IntegrityError:
            return apology("Error", "Username taken")



@app.route("/message_list", methods=["GET", "POST"])
def message_list():
    if request.method == "GET":
        try:
           current_user = session["user_id"]
           temp_message_list = c.execute("SELECT id,from_id,to_id,title,message,time,read_flag,type FROM message_info where to_id = ?",[current_user]).fetchall()
           db.commit()
           all_message_count=len(temp_message_list);

           unread_message_list = c.execute("SELECT id,from_id,to_id,title,message,time,read_flag,type FROM message_info where to_id = ? and read_flag=0",[current_user]).fetchall()
           db.commit()

           unread_message_count=len(unread_message_list);
          
           from_username="";
           to_username="";
           title="";
           message="";
           time1="";
           read_flag=1;

           message_list=[]
           if len(temp_message_list)>0:
              for index in range(0,len(temp_message_list)): 

                  message_id=temp_message_list[index][0]               

                  from_id=temp_message_list[index][1]               
                  to_id=temp_message_list[index][2]               

                  title=temp_message_list[index][3]               
                  message=temp_message_list[index][4]
                  time1=temp_message_list[index][5]



                  timeArray = time.localtime(int(time1))  
                  time1= time.strftime("%Y-%m-%d %H:%M:%S", timeArray)  

                  read_flag=str(temp_message_list[index][6])

                  type=str(temp_message_list[index][7])

                  from_user_info= c.execute("SELECT  username FROM users WHERE id = ? ", [temp_message_list[index][1]]).fetchall()[0]
                  from_username=from_user_info[0]

                  to_user_info= c.execute("SELECT  username FROM users WHERE id = ? ", [temp_message_list[index][2]]).fetchall()[0]
                  to_username=to_user_info[0]
                  message_list.append([message_id,from_username,to_username,title,message,time1,read_flag,type,from_id,to_id])
           return render_template("message_list.html",message_list=message_list,all_message_count=all_message_count,unread_message_count=unread_message_count)
        except sqlite3.IntegrityError:
            return apology("Error", "Username taken")





@app.route("/friends_list", methods=["GET", "POST"])
def friends_list():
    # if get request return register template
    if request.method == "GET":
        current_user = session["user_id"]
        leaders=[] 
        like_id_dict={}
        try:
           like_id_list = c.execute("SELECT like_id,from_id FROM  like_info WHERE ( from_id = ? or like_id = ? ) and accepted_flag=1", [current_user,current_user]).fetchall()
           for temp_like_id in like_id_list:
               if int(current_user)!=int(temp_like_id[0]):
                  like_id_dict[temp_like_id[0]]=""
               if int(current_user)!=int(temp_like_id[1]):
                  like_id_dict[temp_like_id[1]]=""

           for like_id in like_id_dict: 
               temp_leaders=c.execute("SELECT username, cash, assets, id FROM users where id = ?",[like_id]).fetchall()
               if len(temp_leaders)>0:
                  leaders.append(temp_leaders[0]) 
           db.commit()
           return render_template("friends_list.html", leaders=leaders, usd=usd,current_username=current_user,current_userid=current_user)
        #if username is not unique alert user
        except sqlite3.IntegrityError:
            return apology("Error", "Username taken")



@app.route("/symbol_search", methods=["GET", "POST"])
def symbol_search():
    if request.method == "GET":
        symbol_search= request.args.get("symbol",'')
        print(symbol_search)
        try:
            symbol_list=[]
            for symbol in code_dict:
                if symbol.startswith(symbol_search):
                   code=code_dict[symbol]
                   fullname=fullname_dict[symbol]
                   temp_tuple=(code,symbol,fullname)
                   symbol_list.append(temp_tuple)
            return render_template("symbol_list.html",symbol_list=symbol_list)
        except sqlite3.IntegrityError:
            return apology("Error", "Username taken")

    # if post request
    elif request.method == "POST":
        symbol_search= request.form.get("symbol",'')
        try:
            symbol_list=[]
            for symbol in code_dict:
                #if symbol_search in symbol:
                if symbol.startswith(symbol_search):
                   code=code_dict[symbol]
                   fullname=fullname_dict[symbol]
                   temp_tuple=(code,symbol,fullname)
                   symbol_list.append(temp_tuple)
            return render_template("symbol_list.html",symbol_list=symbol_list)
        except sqlite3.IntegrityError:
            return apology("Error", "Username taken")



@app.route("/profile", methods=["GET", "POST"])
def profile():
    if request.method == "GET":

        user_id= request.args.get("user_id",'')
        if user_id!="":
           current_user = user_id
        else:
           current_user = session["user_id"]
        user_info= c.execute("SELECT  id,username,cash,fullname,email,phonenumber,facebooklink FROM users WHERE id = :CURRENT_USER", [current_user]).fetchall()[0]
        availables = c.execute("SELECT symbol, sum(quantity) FROM transactions WHERE user_id = :user_id GROUP BY symbol",[current_user]).fetchall()
        for available in availables:
            symbol=available[0]
            quantity=available[1]
            price = c.execute("SELECT price,alarm FROM alarm_info WHERE user_id = :user_id  and symbol = :symbol",[current_user,symbol]).fetchall()
            print(price)
            if len(price)>0:
               availables=[(symbol, quantity,price[0][0],price[0][1])]
            else:
               availables=[(symbol, quantity,0.0,"NO_ALARM")]
        return render_template("profile.html",user_info=user_info,availables=availables)

        symbol_search= request.args.get("symbol",'')
        print(symbol_search)
        try:
            symbol_list=[]
            for symbol in code_dict:
                if symbol_search in symbol:
                   code=code_dict[symbol]
                   fullname=fullname_dict[symbol]
                   temp_tuple=(code,symbol,fullname)
                   symbol_list.append(temp_tuple)
            return render_template("symbol_list.html",symbol_list=symbol_list)
        except sqlite3.IntegrityError:
            return apology("Error", "Username taken")

    # if post request
    elif request.method == "POST":
        symbol_search= request.form.get("symbol",'')
        try:
            symbol_list=[]
            for symbol in code_dict:
                if symbol_search in symbol:
                   code=code_dict[symbol]
                   fullname=fullname_dict[symbol]
                   temp_tuple=(code,symbol,fullname)
                   symbol_list.append(temp_tuple)
            return render_template("symbol_list.html",symbol_list=symbol_list)
        except sqlite3.IntegrityError:
            return apology("Error", "Username taken")



@app.route("/set_price", methods=["GET", "POST"])
def set_price():
    if request.method == "GET":
        current_user = session["user_id"]
        symbol= request.args.get("symbol",'')
        price= request.args.get("price",'')
        return render_template("set_price.html",price=price,symbol=symbol)

    elif request.method == "POST":
        current_user = session["user_id"]
        symbol= request.form.get("symbol",'')
        price= request.form.get("price",'')
        try:
            c.execute("UPDATE alarm_info SET price=? WHERE user_id = ? and symbol=?", (price,(current_user),symbol))
            db.commit()
            return redirect(url_for("profile"))
        except sqlite3.IntegrityError:
            return apology("Error", "Username taken")



#    id INTEGER PRIMARY KEY NOT NULL,
#    username TEXT NOT NULL,
#    hash TEXT NOT NULL,
#    cash REAL DEFAULT 10000.00 NOT NULL,
#    assets DECIMAL DEFAULT 0 NOT NULL
#, 'fullname' varchar, 'email' TEXT, 'phonenumber' TEXT, 'facebooklink' TEXT);
#


@app.route("/modify_user_info", methods=["GET", "POST"])
def modify_user_info():
    if request.method == "GET":
        current_user = session["user_id"]
        user_id=request.args.get("user_id")
        user=c.execute("SELECT username,is_administrator FROM users WHERE id = :user_id", [current_user]).fetchall()[0]
        if len(user)>0:
           if (user[0]=="admin" or user[0]=="administrator" or user[1]=="1" or user[1]==1 ) or (int(current_user)==int(user_id)):
              #c.execute("DELETE FROM users WHERE id = :user_id", [user_id])
              user1=c.execute("SELECT username,hash,assets,cash,fullname,email,phonenumber,facebooklink FROM users WHERE id = :user_id", [user_id]).fetchall()[0]
              db.commit()
              return render_template("modify_user_info.html",user=user1)
           else:
              return redirect(url_for("leaderboard"))

            
    elif request.method == "POST":
        current_user = session["user_id"]

        cash= request.form.get("cash",'')
        password= request.form.get("password",'')
        assets= request.form.get("assets",'')
        fullname= request.form.get("fullname",'')
        email= request.form.get("email",'')
        phonenumber= request.form.get("phonenumber",'')
        facebooklink= request.form.get("facebooklink",'')
        try:
            c.execute("UPDATE users SET   cash=:cash,hash=:password,assets=:assets,fullname=:fullname,email=:email,phonenumber=:phonenumber,facebooklink=:facebooklink WHERE id = :user_id", [cash,password,assets,fullname,email,phonenumber,facebooklink,current_user])
            db.commit()
            return redirect(url_for("index"))
        except sqlite3.IntegrityError:
            return apology("Error", "Username taken")


@app.route("/add_user_info", methods=["GET", "POST"])
def add_user_info():
    if request.method == "GET":
       # current_user = session["user_id"]
        return render_template("add_user_info.html")
    elif request.method == "POST":
        current_user = session["user_id"]
        username = request.form.get("username")
        password = request.form.get("password")
        password_confirm = request.form.get("password-confirm")
        fullname= request.form.get("fullname")
        email= request.form.get("email")
        facebooklink= request.form.get("facebooklink")
        phonenumber= request.form.get("phonenumber")

        # check fields for completion
        if not request.form.get("username"):
            return apology("Error","Forgot Username")
        elif not request.form.get("password"):
            return apology("Error", "Forgot Password")
        elif not request.form.get("password-confirm"):
            return apology("Error", "Forgot Confirmation")

        # if passwords match
        if password == password_confirm:
            # encrypt password
            #hashed = sha256_crypt.encrypt(password)
            hashed = password
            username = re.sub(r'\W+', '', username.lower())
            try:
                # send user details to database
                c.execute("INSERT INTO users(username, hash,fullname,email,phonenumber,facebooklink) VALUES(:username, :hash,:fullname,:email,:phonenumber,:facebooklink)", [username, hashed,fullname,email,phonenumber,facebooklink])
                db.commit()
                return redirect(url_for("user_info_list"))
            # if username is not unique alert user
            except sqlite3.IntegrityError:
                return apology("Error", "Username taken")
        else:
            return apology("Passwords don't match")



@app.route("/delete_user_info", methods=["GET", "POST"])
def delete_user_info():
    if request.method == "GET":
        current_user = session["user_id"]
        user_id=request.args.get("user_id")
        user=c.execute("SELECT username,is_administrator FROM users WHERE id = :user_id", [current_user]).fetchall()[0]
        if len(user)>0:
           if user[0]=="admin" or user[0]=="administrator" or user[1]=="1" or user[1]==1:
              c.execute("DELETE FROM users WHERE id = :user_id", [user_id])
              db.commit()
              return redirect(url_for("user_info_list"))
           else:
              return redirect(url_for("leaderboard"))





@app.route("/add_user_to_be_administrator", methods=["GET", "POST"])
def add_user_to_be_administrator():
    if request.method == "GET":
        current_user = session["user_id"]
        user_id=request.args.get("user_id")
        user=c.execute("update users set is_administrator=1 WHERE id = ?", [user_id])
        db.commit()
        return redirect(url_for("leaderboard"))


@app.route("/delete_user_not_to_be_administrator", methods=["GET", "POST"])
def delete_user_not_to_be_administrator():
    if request.method == "GET":
        #current_user = session["user_id"]
        user_id=request.args.get("user_id")
        user=c.execute("update users set is_administrator=0 WHERE id = ?", [user_id])
        db.commit()
        return redirect(url_for("leaderboard"))



@app.route("/user_info_list", methods=["GET", "POST"])
def user_info_list():
    if request.method == "GET":
        current_user = session["user_id"]
        user=c.execute("SELECT username,is_administrator FROM users WHERE id = :user_id", [current_user]).fetchall()[0]
        if len(user)>0:
           if user[0]=="admin" or user[0]=="administrator" or user[1]=="1" or user[1]==1:
              users = c.execute("SELECT id,username,fullname,phonenumber,facebooklink FROM users").fetchall()
              return render_template("user_info_list.html",users=users,current_username=user[0])
           else: 
              return redirect(url_for("leaderboard")) 




@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    symbol_search = request.args.get('q')
    #query = db_session.query(Movie.title).filter(Movie.title.like('%' + str(search) + '%'))
    #results = [mv[0] for mv in query.all()]
    try:
        symbol_list=[]
        for symbol in code_dict:
            if symbol.startswith(symbol_search):
               code=code_dict[symbol]
               #fullname=fullname_dict[symbol]
               #temp_tuple=(code,symbol,fullname)
               symbol_list.append(symbol)
        return jsonify(matching_results=symbol_list)
        #return render_template("autocomplete.html",symbol_list=symbol_list)
    except sqlite3.IntegrityError:
        return apology("Error", "Username taken")
    #return jsonify(matching_results=results)



@app.route('/autocomplete1', methods=['GET'])
def autocomplete1():
    symbol_search = request.args.get('q')
    current_user = session["user_id"]
    symbol_list = c.execute("SELECT symbol FROM  transactions WHERE user_id = ?",[current_user])
    temp_dict={}
    for mv in symbol_list.fetchall():
        temp_dict[mv[0]]=""

    results=[]
    for key in temp_dict:
        results.append(key)    
         
    return jsonify(matching_results=results)


@app.route("/plot", methods=["GET", "POST"])
@login_required
def plot():
    if request.method == "GET":
        symbol = request.args.get("symbol")
        return render_template("plot.html",symbol=symbol)

if __name__ == "__main__":
    app.run(host='0.0.0.0',debug=True,port=8088)

