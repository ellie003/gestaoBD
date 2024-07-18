from flask import Flask, request, render_template, redirect, url_for, flash, session
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DB_HOST = "localhost"
DB_NAME = "novo_banco"
DB_USER = "postgres"
DB_PASS = "0523"

def connect_db():
    return psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)

@app.route('/')
def form():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']

    hashed_password = generate_password_hash(password)

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s)", (username, email, hashed_password))
    conn.commit()

    cursor.close()
    conn.close()

    return 'Dados recebidos e inseridos com sucesso'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user and check_password_hash(user[3], password):  
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['email'] = user[2]
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('dashboard'))

        flash('Login ou senha incorretos', 'danger')
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        user_info = {
            'username': session['username'],
            'email': session['email']
        }
        return render_template('dashboard.html', user=user_info)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
