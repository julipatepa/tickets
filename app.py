from flask import Flask, render_template, request, redirect, url_for, flash, g
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "tu_secreto"
DATABASE = "database.db"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, username FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if user:
        return User(id=user["id"], username=user["username"])
    return None

def get_db():
    if not hasattr(g, '_database'):
        g._database = sqlite3.connect(DATABASE)
        g._database.row_factory = sqlite3.Row
    return g._database

def init_db():
    if not os.path.exists(DATABASE):
        with sqlite3.connect(DATABASE) as db:
            cursor = db.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'Pendiente',
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )''')
            db.commit()

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, '_database'):
        g._database.close()

class LoginForm(FlaskForm):
    username = StringField("Usuario", validators=[DataRequired()])
    password = PasswordField("Contraseña", validators=[DataRequired()])
    submit = SubmitField("Iniciar sesión")

class RegisterForm(FlaskForm):
    username = StringField("Usuario", validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField("Contraseña", validators=[DataRequired(), Length(min=6)])
    submit = SubmitField("Registrarse")

@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        db = get_db()
        cursor = db.cursor()
        password_hash = generate_password_hash(password)
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password_hash))
            db.commit()
            flash("Registro exitoso.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("El usuario ya existe.", "danger")
    return render_template("register.html", form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id, username, password FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        if user and check_password_hash(user["password"], password):
            user_obj = User(id=user["id"], username=user["username"])
            login_user(user_obj, remember=True)  # Keep user logged in across sessions
            flash("Inicio de sesión exitoso", "success")
            return redirect(url_for("index"))
        else:
            flash("Usuario o contraseña incorrectos", "danger")
    return render_template("login.html", form=form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada con éxito.", "info")
    return redirect(url_for("login"))

@app.route("/")
@login_required
def index():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, title, description, status, created_at FROM tickets ORDER BY created_at DESC")
    tickets = cursor.fetchall()
    return render_template("index.html", tickets=tickets)

@app.route("/add_ticket", methods=["POST"])
@login_required
def add_ticket():
    title = request.form.get("title")
    description = request.form.get("description")
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO tickets (title, description) VALUES (?, ?)", (title, description))
    db.commit()
    flash("Ticket agregado exitosamente.", "success")
    return redirect(url_for("index"))

@app.route("/update_status/<int:ticket_id>", methods=["POST"])
@login_required
def update_status(ticket_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE tickets SET status = 'En proceso' WHERE id = ?", (ticket_id,))
    db.commit()
    flash("El ticket ha sido actualizado a 'En proceso'", "success")
    return redirect(url_for("index"))

@app.route("/mark_resolved/<int:ticket_id>", methods=["POST"])
@login_required
def mark_resolved(ticket_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE tickets SET status = 'Solucionado' WHERE id = ?", (ticket_id,))
    db.commit()
    flash("El ticket ha sido marcado como 'Solucionado'", "success")
    return redirect(url_for("index"))

@app.route("/delete_ticket/<int:ticket_id>", methods=["POST"])
@login_required
def delete_ticket(ticket_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))
    db.commit()
    flash("El ticket ha sido eliminado", "danger")
    return redirect(url_for("index"))

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
