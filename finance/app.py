import os
import datetime
import pytz

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, check_username, check_password

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():

    # download the portfolio of the current user

    # check if the current user has a portfolio
    stock_value = 0
    # time = datetime.datetime.now(pytz.timezone("US/Eastern")).strftime('%Y-%m-%d')
    if (user_portfolio := (db.execute("SELECT * FROM holdings WHERE user_id = ?", session["user_id"]))):

        for holding in user_portfolio:
            # update dictionaries in the user portfolio with the current market price of each stock
            stock_info = lookup(holding["ticker"])
            holding["price"] = stock_info["price"]
            # holding["time"] = stock_info["time"].strftime('%Y-%m-%d')
            stock_value += (holding["price"] * holding["units_held"])

    user_info = db.execute("SELECT username, cash FROM users WHERE id = ?", session["user_id"])[0]

    return render_template("index.html", user_portfolio=user_portfolio, usd=usd, user_info=user_info, stock_value=stock_value)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        if (not (symbol := request.form.get("symbol"))) or (not (symbol_dict := lookup(symbol))):
            return apology("enter a valid stock symbol")

        try:
            # Try to convert the input to an integer
            number_shares = request.form.get("shares")
            num = int(number_shares)

            # Check if the number is positive and does not have a decimal part
            if num < 0 or num != float(number_shares):
                return apology("enter a positive whole number of shares")
        except ValueError:
            # If conversion to int fails, or the number is not positive
            return apology("enter a positive whole number of shares")
        user_cash_dict = (db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"]))
        user_cash = user_cash_dict[0]['cash']

        if int(user_cash) < (cost := symbol_dict["price"] * num):
            print(cost, type(symbol_dict["price"]))
            return apology("Not enough cash")

        # calculate new cash amount
        user_cash -= cost

        # update user cash amount
        db.execute("UPDATE users SET cash = ? WHERE id = ?", user_cash, session["user_id"])

        # add transaction to the transactions table
        db.execute("INSERT INTO transactions (user_id, ticker, price, volume, transaction_type) VALUES (?,?,?,?,?)",
                   session["user_id"], symbol_dict["symbol"], symbol_dict["price"], num, 'BUY')

        # update holdings:
        # if holdings exist already, update existing holdings
        if (user_holdings := db.execute("SELECT * FROM holdings WHERE user_id = ? AND ticker = ?", session["user_id"], symbol_dict["symbol"])):

            user_holdings = user_holdings[0]
            # update units held in memory
            user_holdings["units_held"] += num

            # update total cost in memory
            user_holdings["cost"] += cost

            # update holdings table on disc
            db.execute("UPDATE holdings SET units_held = ?, cost = ? WHERE user_id = ? AND ticker = ?",
                       user_holdings["units_held"], user_holdings["cost"], session["user_id"], symbol_dict["symbol"])

        # else if no holdings exist for that user, make a new entry in the holdings table
        else:
            db.execute("INSERT INTO holdings (user_id, ticker, units_held, cost) VALUES (?,?,?,?)",
                       session["user_id"], symbol_dict["symbol"], num, cost)

        # at this point it's a success so we want a pop-up saying as much
        return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/changePassword", methods=["GET", "POST"])
@login_required
def changePassword():
    """ Allow user to change passwords"""

    if request.method == "POST":

        # Download current password hash from disc
        current_password_hash = db.execute("SELECT hash FROM users WHERE id = ?", session["user_id"])[0]["hash"]
        print(current_password_hash)

        # Ensure current password was submitted
        if not (current_passw_attempt := request.form.get("currentPassword")):
            return apology("must provide current password", 403)

        # Ensure new password was submitted
        elif not (new_passw := request.form.get("newPassword")):
            return apology("must provide new password", 403)

        # Ensure password confirmation was submitted
        elif not (new_passw_conf := request.form.get("confirmNewPassword")):
            return apology("must provide password confirmation", 403)

        # Ensure current password is correct
        elif not (check_password_hash(current_password_hash, current_passw_attempt)):
            return apology("Current password not entered correctly", 403)

        # Ensure new password matches correct format
        elif not (check_password(new_passw)):
            return apology("New password must contain an uppercase letter, a number, a symbol in {!@#$%^&*_} and be 8-30 characters")

        # Ensure passwords match
        elif not (new_passw == new_passw_conf):
            return apology("New Password and Confirmation must match", 403)

        # Ensure new password is different form old
        elif (check_password_hash(current_password_hash, new_passw)):
            return apology("New Password must be different from current password", 403)

        else:
            db.execute("UPDATE users SET hash = ? WHERE id = ?", generate_password_hash(new_passw), session["user_id"])
            return redirect("/")

    else:
        return render_template("changePassword.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    # Download user transactions from disc
    user_transactions = db.execute("SELECT * FROM transactions WHERE user_id = ?", session["user_id"])

    # Download user_information from disc
    user_info = db.execute("SELECT username, cash FROM users WHERE id = ?", session["user_id"])[0]

    time = datetime.datetime.now(pytz.timezone("US/Eastern")).strftime('%Y-%m-%d')

    return render_template("history.html", user_transactions=user_transactions, usd=usd, user_info=user_info)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        if (not (symbol := request.form.get("symbol"))) or (not (symbol_dict := lookup(symbol))):
            return apology("enter a valid stock symbol")
        else:
            return render_template("quoted.html", symbol_dict=symbol_dict, usd=usd)

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    session.clear()

    if request.method == "POST":


        # Ensure username was submitted
        if not (usern_reg := request.form.get("username").lower()):
            return apology("must provide username", 400)

        # Ensure username not already taken
        elif (db.execute("SELECT username FROM users WHERE username = ?", usern_reg)):
            return apology("username already exists", 400)

        # Ensure password was submitted
        elif not (passw_reg := request.form.get("password")):
            return apology("must provide password", 400)

        # Ensure password confirmation was submitted
        elif not (passw_conf := request.form.get("confirmation")):
            return apology("must provide password confirmation", 400)

        # Ensure password matches format
        elif not (check_password(passw_reg)):
            return apology("Password must contain an uppercase letter, number, symbol in {!@#$%^&*_} and be of 8-30 characters", 400)

        # Ensure passwords match
        elif not (passw_reg == passw_conf):
            return apology("Passwords must match", 400)

        db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", usern_reg, generate_password_hash(passw_reg))

        user_id = db.execute("SELECT id FROM users WHERE username = ?", usern_reg)[0]["id"]

        session["user_id"] = user_id

        return redirect("/")

# If accessed via a GET request
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    if request.method == "POST":
        if (not (symbol := request.form.get("symbol"))) or (not (symbol_dict := lookup(symbol))):
            return apology("enter a valid stock symbol")

        try:
            # Try to convert the input to an integer
            number_shares = request.form.get("shares")
            if not number_shares:
                return apology("enter a positive whole number of shares")
            num = int(number_shares)

            # Check if the number is positive and does not have a decimal part
            if num < 0 or num != float(number_shares):
                return apology("enter a positive whole number of shares")
        except ValueError:
            # If conversion to int fails, or the number is not positive
            return apology("enter a positive whole number of shares")

        # download the current stock holding of the user
        if not (user_stock_holding := (db.execute("SELECT * FROM holdings WHERE user_id = ? AND ticker = ?", session["user_id"], symbol))):
            return apology("You don't own any of this stock")

        # turn user_stock holding from a list of a singular dict to just a dict (assuming that list is non-empty as verified above)
        user_stock_holding = user_stock_holding[0]

        if user_stock_holding['units_held'] < (num):
            return apology("Can't sell down more than you own")

        # add transaction to transactions table
        db.execute("INSERT INTO transactions (user_id, ticker, price, volume, transaction_type) VALUES (?,?,?,?,?)",
                   session["user_id"], symbol_dict["symbol"], symbol_dict["price"], num, 'SELL')

        # download current cash
        user_cash_dict = (db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"]))
        user_cash = user_cash_dict[0]['cash']

        # calculate value sold
        value_sold = num * symbol_dict["price"]

        # update current cash (in memory)
        user_cash += value_sold

        # update user cash amount (in disc)
        db.execute("UPDATE users SET cash = ? WHERE id = ?", user_cash, session["user_id"])

        # update holdings in memory
        user_stock_holding['units_held'] -= num

        # Update stock_holding if non-zero, else delete the holding entry if stock_held is zero
        if (user_stock_holding['units_held']):
            db.execute("UPDATE holdings SET units_held = ? WHERE user_id = ? AND ticker = ?",
                       user_stock_holding['units_held'], session["user_id"], symbol)
        else:
            db.execute("DELETE FROM holdings WHERE user_id = ? AND ticker = ?", session["user_id"], symbol)

        # redirect to the homepage
        return redirect("/")

    else:
        holdings = db.execute("SELECT DISTINCT ticker FROM holdings WHERE user_id = ?", session["user_id"])
        holdings = [holding["ticker"] for holding in holdings]
        return render_template("sell.html", holdings=holdings)
