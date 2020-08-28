import os
import requests, datetime, json, random2

from random2 import randint
from datetime import date
from flask import Flask, session, render_template, request, redirect, url_for, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    if 'user' in session:
        return redirect(url_for('welcome'))
    return render_template("index.html")


@app.route("/signup")
def signup():
    return render_template("signup.html")


@app.route("/adduser", methods=["POST"])
def adduser():
    newuser = str(request.form.get("newuser"))
    newpass = str(request.form.get("newpass"))

    checknewuser = db.execute("SELECT * FROM users WHERE username=:newuser", {"newuser": newuser}).rowcount

    if checknewuser != 0:
        return render_template("error.html", message="Username already exists. Please try creating account again using a different username.")
    db.execute("INSERT INTO users(username, password) VALUES(:newuser, :newpass)", {"newuser": newuser, "newpass": newpass})
    db.execute("UPDATE users SET savedbooks_id = array_append(savedbooks_id, 0) WHERE username=:newuser", {"newuser": newuser})
    db.execute("UPDATE users SET toreadbooks_id = array_append(toreadbooks_id, 0) WHERE username=:newuser", {"newuser": newuser})
    db.commit()
    return render_template("usercreated.html")


@app.route("/login")
def login():
    if 'user' in session:
        return redirect(url_for('welcome'))
    return render_template("login.html")


@app.route("/loguser", methods=["POST"])
def loguser():
    checkuser = str(request.form.get("checkuser"))
    checkpass = str(request.form.get("checkpass"))

    check = db.execute("SELECT * FROM users WHERE username=:checkuser AND password=:checkpass", {"checkuser": checkuser, "checkpass": checkpass}).rowcount
    checkusername = db.execute("SELECT * FROM users WHERE username=:checkuser", {"checkuser": checkuser}).rowcount

    if check != 0:
        session['user'] = checkuser
        return redirect(url_for('welcome'))
    elif check==0 and checkusername!=0:
        return render_template("error.html", message="Password is incorrect. Plase try logging in again.")
    else:
        return render_template("error.html", message="Username does not exist.") 


@app.route("/welcome")
def welcome():
    checkuser = session.get('user')
    if 'user' in session:
        blcheckblank = db.execute("SELECT * FROM users WHERE 0 = ANY(savedbooks_id) AND username=:checkuser", {"checkuser":checkuser}).rowcount
        bl = []
        if blcheckblank != 0:
            bl.append("a")
        booklist = db.execute("SELECT savedbooks_id FROM users WHERE username=:checkuser", {"checkuser":checkuser})
        for books1 in booklist:
            for book1 in books1:
                for num1 in book1:
                    bl.append(db.execute("SELECT * FROM books WHERE id=:num", {"num":num1}))
        trlcheckblank = db.execute("SELECT * FROM users WHERE 0 = ANY(toreadbooks_id) AND username=:checkuser", {"checkuser":checkuser}).rowcount
        trl =[]
        if trlcheckblank != 0:
            trl.append("a")
        toreadlist = db.execute("SELECT toreadbooks_id FROM users WHERE username=:checkuser", {"checkuser":checkuser})
        for books2 in toreadlist:
            for book2 in books2:
                for num2 in book2:
                    trl.append(db.execute("SELECT * FROM books WHERE id=:num", {"num":num2}))
        checkreviews = db.execute("SELECT review_text FROM reviews JOIN users ON reviews.user_id=users.id WHERE username=:checkuser", {"checkuser": checkuser}).rowcount
        if checkreviews == 0:
            myreviews = "a"
        else:
            myreviews = db.execute("SELECT book_id, title, author, year, rating, review_text, review_title, date FROM users INNER JOIN reviews ON users.id=reviews.user_id INNER JOIN books ON reviews.book_id=books.id WHERE username=:checkuser LIMIT 5", {"checkuser": checkuser})
        return render_template("welcome.html", checkuser=checkuser, bl=bl, trl=trl, myreviews=myreviews)
    return render_template("error.html", message="Not logged in.")

@app.route("/searchbook", methods=["POST"])
def searchbook():
    checkuser = session.get('user')
    if 'user' in session:
        searchbook = str("%"+request.form.get("searchbook")+"%")
        results = db.execute("SELECT * FROM books WHERE LOWER(isbn) LIKE LOWER(:searchbook) OR LOWER(title) LIKE LOWER(:searchbook) OR LOWER(author) LIKE LOWER(:searchbook)", {"searchbook": searchbook})
        return render_template("results.html", results=results, searchbook=searchbook, checkuser=checkuser)
    return render_template("error.html", message="Not logged in.")

@app.route("/random")
def random():
    checkuser = session.get('user')
    if 'user' in session:
        book_id = random2.randint(5001, 10000)
        return redirect(url_for('book', book_id=book_id))
    return render_template("error.html", message="Not logged in.")

@app.route("/newreviews")
def newreviews():
    checkuser = session.get('user')
    if 'user' in session:
        newreviews = db.execute("SELECT * FROM users INNER JOIN reviews ON users.id=reviews.user_id INNER JOIN books ON reviews.book_id=books.id ORDER BY date DESC LIMIT 10")
        return render_template("newreviews.html", newreviews=newreviews, checkuser=checkuser)
    return render_template("error.html", message="Not logged in.")

@app.route("/book/<int:book_id>", methods=["GET", "POST"])
def book(book_id):
    checkuser = session.get('user')
    if 'user' in session:
        if 'result' in session:
            session.pop('result', None)
        result = db.execute("SELECT * FROM books WHERE id=:book_id", {"book_id": book_id}).fetchone()
        if result is None:
            return render_template("error.html", message="No such book."), 404
        session['result'] = result
        checksavebl = db.execute("SELECT * FROM users WHERE :book_id = ANY(savedbooks_id) AND username=:checkuser", {"book_id":book_id, "checkuser":checkuser}).rowcount
        saved = None
        if checksavebl !=0:
            saved = True
        checksavetrl = db.execute("SELECT * FROM users WHERE :book_id = ANY(toreadbooks_id) AND username=:checkuser", {"book_id":book_id, "checkuser":checkuser}).rowcount
        toread = None
        if checksavetrl !=0:
            toread = True
        isbn = db.execute("SELECT isbn FROM books WHERE id=:book_id", {"book_id": book_id}).fetchone()
        greads = requests.get("https://www.goodreads.com/book/review_counts.json?key=OgKnnRjEoOYJixzAGM60wg&isbns=" + isbn[0])
        if greads.status_code != 200:
            return render_template("bookpage.html", checkuser=checkuser, result=result, rating="ERROR: API request unsuccessful.")
        data = greads.json()
        grrating = data["books"][0]["average_rating"]
        ourrating = db.execute("SELECT ROUND(AVG(rating), 1) FROM reviews WHERE book_id=:book_id", {"book_id": book_id}).fetchone()
        blrating = ourrating[0]
        checkrating = db.execute("SELECT * FROM reviews WHERE book_id=:book_id", {"book_id": book_id}).rowcount
        if checkrating == 0:
            reviews = "a"
        else:
            reviews = db.execute("SELECT * FROM users JOIN reviews ON reviews.user_id=users.id WHERE book_id=:book_id", {"book_id": book_id}).fetchall()
        return render_template("bookpage.html", checkuser=checkuser, result=result, grrating=grrating, reviews=reviews, blrating=blrating, saved=saved, toread=toread)
    return render_template("error.html", message="Not logged in.")

@app.route("/book/bookapi/<int:book_id>")
def book_api(book_id):
    checkuser = session.get('user')
    if 'user' in session:
        result = db.execute("SELECT * FROM books WHERE id=:book_id", {"book_id": book_id}).fetchone()
        rating = db.execute("SELECT ROUND(AVG(rating), 1) FROM reviews WHERE book_id=:book_id", {"book_id": book_id}).fetchone()
        if result is None:
            return jsonify({"error": "Invalid book_id"}), 422
        try:
            blrating = float(rating[0])
        except TypeError:
            return jsonify({
                "title": result.title,
                "author": result.author,
                "year": result.year,
                "isbn": result.isbn,
                "booklist_rating": "None"
            })
        return jsonify({
            "title": result.title,
            "author": result.author,
            "year": result.year,
            "isbn": result.isbn,
            "booklist_rating": blrating
        })
    return render_template("error.html", message="Not logged in.")

@app.route("/book/reviewsapi/<int:book_id>")
def reviews_api(book_id):
    checkuser = session.get('user')
    if 'user' in session:
        result = db.execute("SELECT * FROM books WHERE id=:book_id", {"book_id": book_id}).fetchone()
        reviews = db.execute("SELECT row_to_json(data) FROM (SELECT username, date, review_title, review_text, rating FROM reviews JOIN users ON reviews.user_id=users.id WHERE book_id=:book_id ORDER BY date DESC LIMIT 5) AS data", {"book_id": book_id}).fetchall()
        if result is None:
            return jsonify({"error": "Invalid book_id"}), 422
        return jsonify({
            "reviews": [dict(row) for row in reviews]
        })
    return render_template("error.html", message="Not logged in.")

@app.route("/book/<int:book_id>/writereview", methods=["POST"])
def writereview(book_id):
    checkuser = session.get('user')
    if 'user' in session:
        result = session.get('result')
        titlereview = str(request.form.get("titlereview"))
        writereview = str(request.form.get("writereview"))
        rating = float(request.form.get("rating"))
        session['titlereview'] = titlereview
        session['writereview'] = writereview
        session['rating'] = rating
        return render_template("checkreview.html", message="Please confirm to post your review online.", rating=rating, titlereview=titlereview, writereview=writereview, result=result, checkuser=checkuser)
    return render_template("error.html", message="Not logged in.")

@app.route("/book/<int:book_id>/checkreview", methods=["POST"])
def checkreview(book_id):
    checkuser = session.get('user')
    checkuser_id = db.execute("SELECT id FROM users WHERE username=:checkuser", {"checkuser":checkuser}).fetchone()
    user_id = checkuser_id[0]
    if 'user' in session:
        titlereview = session.get('titlereview')
        writereview = session.get('writereview')
        rating = session.get('rating')
        result = session.get('result')
        reviewdate = date.today()
        if 'writereview' and 'titlereview' in session:
            db.execute("INSERT INTO reviews(date, rating, review_title, review_text, user_id, book_id) VALUES(:date, :rating, :title, :text, :user_id, :book_id)", {"date":reviewdate, "rating": rating, "title":titlereview, "text":writereview, "user_id":user_id, "book_id":book_id})
            db.commit()
            session.pop('titlereview', None)
            session.pop('writereview', None)
            return render_template("addreview.html", result=result, checkuser=checkuser)
    return render_template("error.html", message="Not logged in.")

@app.route("/book/<int:book_id>/savebook")
def savebook(book_id):
    checkuser = session.get('user')
    if 'user' in session:
        checkbook = db.execute("SELECT * FROM books WHERE id=:book_id", {"book_id": book_id}).fetchone()
        if checkbook is None:
            return render_template("error.html", message="No such book."), 404
        result = session.get('result')
        checksavebl = db.execute("SELECT * FROM users WHERE :book_id = ANY(savedbooks_id) AND username=:checkuser", {"book_id":book_id, "checkuser":checkuser}).rowcount
        if checksavebl != 0:
            return render_template("inlist.html", result=result), 424
        checkblank = db.execute("SELECT * FROM users WHERE 0 = ANY(savedbooks_id) AND username=:checkuser", {"checkuser":checkuser}).rowcount
        if checkblank !=0:
            db.execute("UPDATE users SET savedbooks_id = array_remove(savedbooks_id, 0) WHERE username=:checkuser", {"checkuser": checkuser})
        db.execute("UPDATE users SET savedbooks_id = array_append(savedbooks_id, :book_id) WHERE username=:checkuser", {"book_id":book_id, "checkuser":checkuser})
        db.commit()
        return render_template("added.html", result=result, checkuser=checkuser)
    return render_template("error.html", message="Not logged in.")

@app.route("/book/<int:book_id>/toreadbook")
def toreadbook(book_id):
    checkuser = session.get('user')
    if 'user' in session:
        checkbook = db.execute("SELECT * FROM books WHERE id=:book_id", {"book_id": book_id}).fetchone()
        if checkbook is None:
            return render_template("error.html", message="No such book."), 404
        result = session.get('result')
        checksavetrl = db.execute("SELECT * FROM users WHERE :book_id = ANY(toreadbooks_id) AND username=:checkuser", {"book_id":book_id, "checkuser":checkuser}).rowcount
        if checksavetrl != 0:
            return render_template("inlist.html", result=result), 424
        checkblank = db.execute("SELECT * FROM users WHERE 0 = ANY(toreadbooks_id) AND username=:checkuser", {"checkuser":checkuser}).rowcount
        if checkblank !=0:
            db.execute("UPDATE users SET toreadbooks_id = array_remove(toreadbooks_id, 0) WHERE username=:checkuser", {"checkuser": checkuser})
        db.execute("UPDATE users SET toreadbooks_id = array_append(toreadbooks_id, :book_id) WHERE username=:checkuser", {"book_id":book_id, "checkuser":checkuser})
        db.commit()
        return render_template("added.html", result=result, checkuser=checkuser)
    return render_template("error.html", message="Not logged in.")

@app.route("/book/<int:book_id>/removesaved")
def removesaved(book_id):
    checkuser = session.get('user')
    if 'user' in session:
        checkbook = db.execute("SELECT * FROM books WHERE id=:book_id", {"book_id": book_id}).fetchone()
        if checkbook is None:
            return render_template("error.html", message="No such book."), 404
        result = session.get('result')
        checkremove = db.execute("SELECT * FROM users WHERE :book_id = ANY(savedbooks_id) AND username=:checkuser", {"book_id":book_id, "checkuser":checkuser}).rowcount
        if checkremove == 0:
            return render_template("error.html", message="This book is not in your list"), 424
        db.execute("UPDATE users SET savedbooks_id = array_remove(savedbooks_id, :book_id) WHERE username=:checkuser", {"book_id": book_id, "checkuser": checkuser})
        checkzero = db.execute("SELECT savedbooks_id FROM users WHERE array_lower(savedbooks_id, 1) is NULL AND username=:checkuser", {"checkuser":checkuser}).rowcount
        if checkzero != 0:
            db.execute("UPDATE users SET savedbooks_id = array_append(savedbooks_id, 0) WHERE username=:checkuser", {"checkuser": checkuser})
            db.commit()
        return render_template("removed.html", checkuser=checkuser, result=result)
    return render_template("error.html", message="Not logged in.")

@app.route("/book/<int:book_id>/removetoread")
def removetoread(book_id):
    checkuser = session.get('user')
    if 'user' in session:
        checkbook = db.execute("SELECT * FROM books WHERE id=:book_id", {"book_id": book_id}).fetchone()
        if checkbook is None:
            return render_template("error.html", message="No such book."), 404
        result = session.get('result')
        checkremove = db.execute("SELECT * FROM users WHERE :book_id = ANY(toreadbooks_id) AND username=:checkuser", {"book_id":book_id, "checkuser":checkuser}).rowcount
        if checkremove == 0:
            return render_template("error.html", message="This book is not in your list"), 424
        db.execute("UPDATE users SET toreadbooks_id = array_remove(toreadbooks_id, :book_id) WHERE username=:checkuser", {"book_id": book_id, "checkuser": checkuser})
        checkzero = db.execute("SELECT toreadbooks_id FROM users WHERE array_lower(toreadbooks_id, 1) is NULL AND username=:checkuser", {"checkuser":checkuser}).rowcount
        if checkzero != 0:
            db.execute("UPDATE users SET toreadbooks_id = array_append(toreadbooks_id, 0) WHERE username=:checkuser", {"checkuser": checkuser})
            db.commit()
        return render_template("removed.html", checkuser=checkuser, result=result)
    return render_template("error.html", message="Not logged in.")

@app.route("/logout")
def logout():
    session.pop('user', None)
    return render_template("out.html")

if __name__=="__main__":
    index()