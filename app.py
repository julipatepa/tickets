from flask import Flask, render_template, request, redirect, url_for, flash, g
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
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
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, username, role FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    if user:
        return User(id=user["id"], username=user["username"], role=user["role"])
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
                priority TEXT DEFAULT 'Media',
                status TEXT DEFAULT 'Pendiente',
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                user_id INTEGER DEFAULT NULL
            )''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'usuario'
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
    role = SelectField("Tipo de cuenta", choices=[("empresa", "Empresa"), ("usuario", "Usuario")])
    submit = SubmitField("Registrarse")

@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        role = form.role.data
        db = get_db()
        cursor = db.cursor()
        password_hash = generate_password_hash(password)
        try:
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, password_hash, role))
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
        cursor.execute("SELECT id, username, password, role FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        if user and check_password_hash(user["password"], password):
            user_obj = User(id=user["id"], username=user["username"], role=user["role"])
            login_user(user_obj, remember=True)
            flash("Inicio de sesión exitoso", "success")
            if user["role"] == "usuario":
                return redirect(url_for("mis_tickets"))
            else:
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
    cursor.execute("SELECT id, title, description, priority, status, created_at FROM tickets ORDER BY created_at DESC")
    tickets = cursor.fetchall()
    return render_template("index.html", tickets=tickets)

@app.route("/add_ticket", methods=["POST"])
@login_required
def add_ticket():
    if current_user.role != "empresa":
        flash("No tenés permiso para crear tickets.", "danger")
        return redirect(url_for("index"))

    title = request.form.get("title")
    description = request.form.get("description")
    priority = request.form.get("priority")

    db = get_db()
    cursor = db.cursor()

    # Asignar el ticket al primer usuario común (usuario)
    cursor.execute("SELECT id FROM users WHERE role = 'usuario' LIMIT 1")
    user = cursor.fetchone()
    user_id = user["id"] if user else None

    cursor.execute(
        "INSERT INTO tickets (title, description, priority, user_id) VALUES (?, ?, ?, ?)",
        (title, description, priority, user_id)
    )
    db.commit()
    flash("Ticket agregado exitosamente.", "success")
    return redirect(url_for("index"))

@app.route("/update_status/<int:ticket_id>", methods=["POST"])
@login_required
def update_status(ticket_id):
    if current_user.role != "empresa":
        flash("No tenés permiso para actualizar tickets.", "danger")
        return redirect(url_for("index"))

    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE tickets SET status = 'En proceso' WHERE id = ?", (ticket_id,))
    db.commit()
    flash("El ticket ha sido actualizado a 'En proceso'", "success")
    return redirect(url_for("index"))

@app.route("/mark_resolved/<int:ticket_id>", methods=["POST"])
@login_required
def mark_resolved(ticket_id):
    if current_user.role != "empresa":
        flash("No tenés permiso para resolver tickets.", "danger")
        return redirect(url_for("index"))

    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE tickets SET status = 'Solucionado' WHERE id = ?", (ticket_id,))
    db.commit()
    flash("El ticket ha sido marcado como 'Solucionado'", "success")
    return redirect(url_for("index"))

@app.route("/delete_ticket/<int:ticket_id>", methods=["POST"])
@login_required
def delete_ticket(ticket_id):
    if current_user.role != "empresa":
        flash("No tenés permiso para eliminar tickets.", "danger")
        return redirect(url_for("index"))

    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))
    db.commit()
    flash("El ticket ha sido eliminado", "danger")
    return redirect(url_for("index"))

@app.route("/mis_tickets")
@login_required
def mis_tickets():
    if current_user.role != "usuario":
        flash("Acceso solo para usuarios comunes.", "danger")
        return redirect(url_for("index"))

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT title, description, priority, status, created_at FROM tickets WHERE user_id = ? ORDER BY created_at DESC",
        (current_user.id,)
    )
    tickets = cursor.fetchall()
    return render_template("tickets_usuario.html", tickets=tickets)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
