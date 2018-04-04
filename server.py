"""Movie Ratings."""

from jinja2 import StrictUndefined
from flask import Flask
from flask_debugtoolbar import DebugToolbarExtension
from model import connect_to_db, db
from flask import (Flask, render_template, redirect, request, flash,
                   session)
from model import User, Rating, Movie, connect_to_db, db
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


app = Flask(__name__)

# Required to use Flask sessions and the debug toolbar
app.secret_key = "ABC"

# Normally, if you use an undefined variable in Jinja2, it fails
# silently. This is horrible. Fix this so that, instead, it raises an
# error.
app.jinja_env.undefined = StrictUndefined


@app.route('/')
def index():
    """Homepage."""
    return render_template("homepage.html")


@app.route("/users")
def user_list():
    """Show list of users."""

    users = User.query.all()
    return render_template("user_list.html", users=users)


@app.route("/register", methods=["GET"])
def register_form():

    return render_template("register_form.html")


@app.route("/register", methods=["POST"])
def register_process():

    email = request.form.get('email')
    password = request.form.get('password')
    age = request.form.get('age')
    zipcode = request.form.get('zipcode')
    user = User(email=email, password=password, age=age, zipcode=zipcode)

    if db.session.query(User.email == email) is not None:
        db.session.add(user)
        db.session.commit()

    return redirect("/")


@app.route("/login")
def login_form():

    return render_template("login.html")


@app.route("/login", methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    try:
        user = db.session.query(User).filter(User.email == email).one()

    except NoResultFound:
        flash('Please register first.')
        return redirect('/register')

    except MultipleResultsFound:
        flash('Multiple Accounts With That Email')
        return redirect('/')

    if user.password == password:
        session["user"] = email
        flash('Logged In')
        return redirect('/users/' + str(user.user_id))
    else:
        flash('Incorrect Username and/or Password')
        return redirect('/login')


@app.route('/users/<user_id>/')
def user_profile(user_id):
    user = db.session.query(User).filter(User.user_id == user_id).one()
    age = user.age
    zipcode = user.zipcode
    ratings = db.session.query(Rating).filter(Rating.user_id == user_id).all()

    return render_template("user_profile.html", age=age, zipcode=zipcode, ratings=ratings)


@app.route("/logout")
def logout():
    session.pop('user')
    return redirect('/')


@app.route("/movies")
def movie_list():
    """Show list of movies."""

    movies = Movie.query.order_by('title').all()
    return render_template("movie_list.html", movies=movies)


@app.route('/movies/<movie_id>/')
def movie_profile(movie_id):
    movie = db.session.query(Movie).filter(Movie.movie_id == movie_id).one()
    ratings = db.session.query(Rating).filter(Rating.movie_id == movie_id).all()

    return render_template("movie_profile.html", ratings=ratings, movie=movie)


if __name__ == "__main__":
    # We have to set debug=True here, since it has to be True at the
    # point that we invoke the DebugToolbarExtension
    app.debug = True
    # make sure templates, etc. are not cached in debug mode
    app.jinja_env.auto_reload = app.debug

    connect_to_db(app)
    app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
    # Use the DebugToolbar
    DebugToolbarExtension(app)

    app.run(port=5000, host='0.0.0.0')
