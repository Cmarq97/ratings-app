"""Movie Ratings."""

from jinja2 import StrictUndefined
from flask import Flask
from flask_debugtoolbar import DebugToolbarExtension
from model import connect_to_db, db
from flask import (Flask, render_template, redirect, request, flash,
                   session)
from model import User, Rating, Movie, connect_to_db, db
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
import correlation

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
    """Show registration form"""

    return render_template("register_form.html")


@app.route("/register", methods=["POST"])
def register_process():
    """Process registration form"""

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
    """Show login form"""

    return render_template("login.html")


@app.route("/login", methods=['POST'])
def login():
    """Process login form for user to log in"""

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
        session["user_id"] = user.user_id
        flash('Logged In')
        return redirect('/users/' + str(user.user_id))
    else:
        flash('Incorrect Username and/or Password')
        return redirect('/login')


@app.route('/users/<user_id>/')
def user_profile(user_id):
    """Show user profile page"""

    user = db.session.query(User).filter(User.user_id == user_id).one()
    age = user.age
    zipcode = user.zipcode
    ratings = db.session.query(Rating).filter(Rating.user_id == user_id).all()

    return render_template("user_profile.html", age=age, zipcode=zipcode, ratings=ratings)


@app.route("/logout")
def logout():
    """Log out user and redirect to home page"""

    session.pop('user')
    return redirect('/')


@app.route("/movies")
def movie_list():
    """Show list of movies."""

    movies = Movie.query.order_by('title').all()
    return render_template("movie_list.html", movies=movies)


@app.route('/movies/<movie_id>/')
def movie_profile(movie_id):
    """Show info about movie.
        If a user is logged in, let them add/edit a rating.
        """

    ratings = db.session.query(Rating).filter(Rating.movie_id == movie_id).all()

    movie = Movie.query.get(movie_id)

    user_id = session.get("user_id")

    if user_id:
        user_rating = Rating.query.filter_by(
            movie_id=movie_id, user_id=user_id).first()

    else:
        user_rating = None

    # Get average rating of movie

    rating_scores = [r.score for r in movie.ratings]
    avg_rating = float(sum(rating_scores)) / len(rating_scores)

    prediction = None

    # Prediction code: only predict if the user hasn't rated it.

    if (not user_rating) and user_id:
        user = User.query.get(user_id)
        if user:
            prediction = user.predict_rating(movie)

    if prediction:
        # User hasn't scored; use our prediction if we made one
        effective_rating = prediction

    elif user_rating:
        # User has already scored for real; use that
        effective_rating = user_rating.score

    else:
        # User hasn't scored, and we couldn't get a prediction
        effective_rating = None

    # Get the eye's rating, either by predicting or using real rating

    the_eye = (User.query.filter_by(email="theeye")
                         .one())
    eye_rating = Rating.query.filter_by(
        user_id=the_eye.user_id, movie_id=movie.movie_id).first()

    if eye_rating is None:
        eye_rating = the_eye.predict_rating(movie)

    else:
        eye_rating = eye_rating.score

    if eye_rating and effective_rating:
        difference = abs(eye_rating - effective_rating)

    else:
        # We couldn't get an eye rating, so we'll skip difference
        difference = None
    # Depending on how different we are from the Eye, choose a
    # message

    BERATEMENT_MESSAGES = [
        "I suppose you don't have such bad taste after all.",
        "I regret every decision that I've ever made that has " +
        "brought me to listen to your opinion.",
        "Words fail me, as your taste in movies has clearly " +
        "failed you.",
        "That movie is great. For a clown to watch. Idiot.",
        "Words cannot express the awfulness of your taste."
    ]

    if difference:
        beratement = BERATEMENT_MESSAGES[int(difference)]

    else:
        beratement = None

    return render_template(
        "movie_profile.html", ratings=ratings,
        movie=movie,
        user_rating=user_rating,
        average=avg_rating,
        prediction=prediction, beratement=beratement
        )


@app.route("/rate_movie", methods=["POST"])
def rate_movie():
    """Allows user to rate movie"""

    movie_id = request.form.get('movie_id')
    user_id = request.form.get('user_id')
    user_rating = request.form.get('rating')

    if 'user' in session:
        rating = db.session.query(Rating).filter((Rating.movie_id == movie_id) & (Rating.user_id == user_id)).first()
        if rating is None:
            db.session.add(Rating(movie_id=movie_id, user_id=user_id, score=user_rating))

        else:
            rating.score = int(user_rating)

        db.session.commit()
    return redirect("/movies/" + movie_id)


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
