# An eCommerce website
#

from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import RegisterForm, LoginForm, AddBookForm, BagForm
import os
import pandas as pd
import random
from dotenv import load_dotenv
import stripe


load_dotenv('.env')
SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
stripe.api_key = SECRET_KEY

ID_API = os.getenv('ID_API')

data_books = pd.read_csv('books.csv')
ID = data_books.book_id
no_books = 12
items = 0
bag = 0
BOOK_LIMIT = 5


app = Flask(__name__)
YOUR_DOMAIN = 'http://127.0.0.1:5000/static/public'


basedir = os.path.abspath(os.path.dirname(__file__))  # Issues with take data for db table file

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
Bootstrap(app)

# #CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] =\
        'sqlite:///' + os.path.join(basedir, 'bag.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)


def get_books():
    choice_books = random.sample(list(ID), no_books)
    return choice_books


@login_manager.user_loader
def load_user(user_id):
    return RegisterUser.query.get(int(user_id))


def make_a_bag():
    with app.app_context():
        db.create_all()
        bag_user = BagUser(
            user_id=current_user.id,
            items=0,
            subtotal=0.0,
            free_shipping=0.0,
            total=0.0,
        )
        db.session.add(bag_user)
        current_user.is_bag = 1
        db.session.commit()
        return redirect(url_for("get_all_tasks", items=items))


def get_bag_items():
    if 'UserMixin' not in str(current_user):
        user_bag = current_user.bag
        bag_id = str(user_bag).split()[1].replace('>]', '')
        requested_bag = BagUser.query.get(int(bag_id))
        return requested_bag.items
    else:
        return items


# #CONFIGURE TABLES
class RegisterUser(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(250), nullable=False)
    is_bag = db.Column(db.Integer, nullable=False)
    bag = relationship('BagUser', back_populates='user')


class BagUser(db.Model):
    __tablename__ = "bag"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(250), db.ForeignKey('user.id'))
    items = db.Column(db.Integer, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    free_shipping = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    user = relationship('RegisterUser', back_populates='bag')
    book_order = relationship('Book', back_populates='bag')


class Book(db.Model):  # book
    __tablename__ = "book_order"  # "books_orders"
    id = db.Column(db.Integer, primary_key=True)
    bag_id = db.Column(db.String(250), db.ForeignKey('bag.id'))
    title_book = db.Column(db.String(500), nullable=False)
    authors = db.Column(db.String(500), nullable=True)
    year = db.Column(db.String(500), nullable=True)
    language_code = db.Column(db.String(250), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    isbn = db.Column(db.String(500), nullable=False)
    price = db.Column(db.String(500), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    bag = relationship('BagUser', back_populates='book_order')  # shopping cart


with app.app_context():  # Add after add a table  or tablename
    db.create_all()
    db.session.commit()


@app.route('/')
def get_all_tasks():
    choice_books = get_books()
    return render_template("index.html", all_books=data_books, index_book=choice_books, items=get_bag_items())


@app.route('/search', methods=['POST'])
def search():
    choice_books = get_books()
    if request.method == "POST":
        search_books = request.form['search_book'].upper()
        book_search = [data_books.book_id[data_books.original_title == book] for book in data_books.original_title
                       if search_books in book.upper()]
        list_book = []
        for book in book_search:
            list_book.append(book.item())
        no_books_find = len(list_book)
        if no_books_find >= 1:
            return render_template("index.html", all_books=data_books, index_book=list_book, items=get_bag_items())
        else:
            flash('No match found!')
            return render_template("index.html", all_books=data_books, index_book=choice_books, items=get_bag_items())
    return render_template("index.html", all_books=data_books, index_book=choice_books, items=get_bag_items())


@app.route('/create-checkout-session', methods=['GET', 'POST'])
def create_checkout_session():
    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price': ID_API,
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=YOUR_DOMAIN + '/success.html',
            cancel_url=YOUR_DOMAIN + '/cancel.html',
        )
    except Exception as e:
        return str(e)

    return redirect(checkout_session.url, code=303)


@app.route('/user_bag', methods=['GET', 'POST'])
def bag():
    user_bag = current_user.bag
    bag_id = str(user_bag).split()[1].replace('>]', '')
    requested_bag = BagUser.query.get(int(bag_id))
    bag_form = BagForm()
    requested_books = requested_bag.book_order
    requested_bag.items = 0
    requested_bag.subtotal = 0.0
    for book in requested_books:
        requested_bag.subtotal += book.subtotal
        requested_bag.items += book.number
    requested_bag.total = requested_bag.subtotal + requested_bag.free_shipping
    db.session.commit()
    if bag_form.validate_on_submit():
        return redirect(url_for('create_checkout_session'))
    return render_template("bag.html", all_books=requested_books, form_submit=bag_form, bag_user=requested_bag,
                           items=requested_bag.items)


@app.route('/details/<int:book_id>', methods=['GET', 'POST'])
def book_details(book_id):
    global items
    form = AddBookForm()
    if form.validate_on_submit():
        if 'UserMixin' not in str(current_user):
            user_bag = current_user.bag
            bag_id = str(user_bag).split()[1].replace('>]', '')
            requested_bag = BagUser.query.get(int(bag_id))
            with app.app_context():
                db.create_all()
                new_book = Book(
                    bag_id=requested_bag.id,
                    title_book=data_books.original_title[book_id-1],
                    authors=data_books.authors[book_id-1],
                    year=str(data_books.original_publication_year[book_id - 1]),
                    language_code=data_books.language_code[book_id - 1],
                    image_url=data_books.image_url[book_id - 1],
                    isbn=data_books.isbn[book_id-1],
                    price=data_books.price[book_id-1],
                    number=1,
                    subtotal=data_books.price[book_id-1]*1,
                )
                db.session.add(new_book)
                db.session.commit()
                return redirect(url_for('bag'))
        else:
            flash("You need to login or register to add a item to cart.")
            return redirect(url_for("login", items=items))
    return render_template("book_details.html", all_books=data_books, index_book=book_id, form=form,
                           items=get_bag_items())


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        password_hash = generate_password_hash(form.password.data, method='pbkdf2:sha256', salt_length=8)
        email = form.email.data
        user = RegisterUser.query.filter_by(email=email).first()
        if not user:
            with app.app_context():
                db.create_all()
                new_user = RegisterUser(email=email, password=password_hash, name=form.name.data, is_bag=0)
                db.session.add(new_user)
                db.session.commit()
                # Log and authenticate user after adding details to database
                login_user(new_user)
                return make_a_bag()
        else:
            flash("You've already signed up with that email, log in instead!")
            return render_template("login.html", form=form, items=items)
    return render_template("register.html", form=form, items=items)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = request.form.get('email')
        password = request.form.get('password')
        user = RegisterUser.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for("get_all_tasks", items=items))
            else:
                flash("Wrong password -Try Again!")
        else:
            flash("That email doesn't Exist! -Try Again!")
            return render_template("login.html", form=form, items=items)
    return render_template("login.html", form=form, items=items)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_tasks', items=items))


@app.route("/plus/<int:book_id>")
@login_required
def plus_book(book_id):
    plus = Book.query.get(book_id)
    if plus.number != BOOK_LIMIT:
        plus.number += 1
    plus.subtotal = plus.number * float(plus.price)
    db.session.commit()
    return redirect(url_for('bag'))


@app.route("/minus/<int:book_id>")
@login_required
def minus_book(book_id):
    minus = Book.query.get(book_id)
    if minus.number != 1:
        minus.number -= 1
    minus.subtotal = minus.number * float(minus.price)
    db.session.commit()
    return redirect(url_for('bag'))


@app.route("/delete_book/<int:book_id>")
@login_required
def delete_book(book_id):
    book_to_delete = Book.query.get(book_id)
    db.session.delete(book_to_delete)
    db.session.commit()
    return redirect(url_for('bag'))


if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000)
