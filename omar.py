# Bn3ml import l kol el libaries el m7tagha fl code 
from flask import Flask, render_template, request, redirect, session, url_for
import json
import redis
import os

# ba3ml intialization l flask app
app = Flask(__name__)

# Secret key is used by Flask to securely sign the session cookies
app.secret_key = "supersecretkey"

redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_port = int(os.getenv('REDIS_PORT', 6379))
redis_client = redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)

BOOKS_KEY = "books"
USERS_KEY = "users"


def save_books(books):
    redis_client.set(BOOKS_KEY, json.dumps(books))

def load_books():
    books_data = redis_client.get(BOOKS_KEY)
    if not books_data:
        return []
    
    books = json.loads(books_data)
    changed = False
    for b in books:
        if "borrowed_by" not in b:
            b["borrowed_by"] = None
            changed = True
        if "image" not in b:
            b["image"] = "bookgh.jpg"
            changed = True
    if changed:
        save_books(books)
    
    return books


def load_users():
    users_data = redis_client.get(USERS_KEY)
    if not users_data:
        return []
    return json.loads(users_data)

def save_users(users):
    redis_client.set(USERS_KEY, json.dumps(users))

def init_admin():
    users = load_users()
    admin_exists = any(u["username"].lower() == "superuser1" for u in users)
    
    if not admin_exists:
        users.append({"username": "superuser1", "password": "123", "role": "admin"})
        save_users(users)
        print("Admin user created: superuser1/123")


@app.route("/")
def landing():
    return render_template("landing.html", hide_nav=True)

@app.route("/home")
def home():
    if "username" not in session:
        return redirect(url_for("login"))

    query = request.args.get("q", "")
    books = load_books()
    if query:
        q = query.lower()
        books = [b for b in books if q in b["title"].lower() or q in b["author"].lower()]

    return render_template(
        "home.html",
        books=books,
        role=session.get("role"),            
        query=query,
        current_user=(session.get("username", "") or "").lower()
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip().lower()
        password = request.form["password"]

        users = load_users()
        user = next((u for u in users if u["username"].lower() == username and u["password"] == password), None)

        if user:
            session["username"] = username
            session["role"] = user["role"]
            print(f"User {username} logged in with role: {user['role']}")
            return redirect(url_for("home"))
        else:
            return render_template("login.html", error="Invalid credentials", hide_nav=True)

    return render_template("login.html", hide_nav=True)  


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip().lower()
        password = request.form["password"]

        users = load_users()
        if any(u["username"].lower() == username for u in users):
            return render_template("signup.html", error="Username already exists", hide_nav=True)

        users.append({"username": username, "password": password, "role": "user"})
        save_users(users)
        return redirect(url_for("login"))

    return render_template("signup.html", hide_nav=True)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/add", methods=["GET", "POST"])
def add_book():
    if session.get("role") != "admin":
        return "Unauthorized", 403

    if request.method == "POST":
        title = request.form["title"].strip()
        author = request.form["author"].strip()
        image = request.form.get("image", "").strip() or "bookgh.jpg"

        books = load_books()
        new_book = {"title": title, "author": author, "image": image, "borrowed_by": None}
        books.append(new_book)
        save_books(books)
        return redirect(url_for("home"))

    return render_template("add_book.html")


@app.route("/delete/<string:title>/<string:author>")
def delete_book(title, author):
    if session.get("role") != "admin":
        
        return "Unauthorized", 403

    books = load_books()
    books = [b for b in books if not (b["title"] == title and b["author"] == author)]
    save_books(books)
    return redirect(url_for("home"))


@app.route("/borrow/<string:title>/<string:author>", methods=["POST"])
def borrow_book(title, author):
    if "username" not in session:
        return redirect(url_for("login"))

    books = load_books()
    for book in books:
        if book["title"] == title and book["author"] == author:
            if not book.get("borrowed_by"):
                book["borrowed_by"] = session["username"].strip().lower()
                save_books(books)
            break
    return redirect(url_for("home"))


@app.route("/return/<string:title>/<string:author>", methods=["POST"])
def return_book(title, author):
    if "username" not in session:
        return redirect(url_for("login"))

    books = load_books()
    for book in books:
        if book["title"] == title and book["author"] == author:
            if book.get("borrowed_by") and book["borrowed_by"].lower() == session["username"].lower():
                book["borrowed_by"] = None
                save_books(books)
            break
    return redirect(url_for("home"))


if __name__ == "__main__":
    #init_admin() 
    app.run(host='0.0.0.0', debug=True, port=5001)
