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
    telefone = request.form['telefone']
    password = request.form['password']
    cep = request.form['cep']
    rua = request.form['rua']
    bairro = request.form['bairro']
    cidade = request.form['cidade']
    uf = request.form['uf']

    hashed_password = generate_password_hash(password)

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("INSERT INTO Usuarios (nome, email, senha) VALUES (%s, %s, %s) RETURNING ID_user", (username, email, hashed_password))
    user_id = cursor.fetchone()[0]
    
    cursor.execute("INSERT INTO Telefones (ID_user, telefone) VALUES (%s, %s)", (user_id, telefone))
    
    cursor.execute("INSERT INTO Endereco (ID_user, cep, rua, bairro, cidade, uf) VALUES (%s, %s, %s, %s, %s, %s)", 
                   (user_id, cep, rua, bairro, cidade, uf))
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

        cursor.execute("SELECT * FROM Usuarios WHERE email = %s", (email,))
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

        conn = connect_db()
        cursor = conn.cursor()

        # Consulta para obter consumo e detalhes do dispositivo
        cursor.execute("""
        SELECT 
        c.id_consumo, 
        c.data, 
        c.hora, 
        c.quantidade, 
        c.recurso, 
        d.nome AS dispositivo_nome, 
        d.tipo AS dispositivo_tipo, 
        d.comodo AS dispositivo_comodo 
    FROM 
        Consumo c
    JOIN 
        Dispositivos d ON CAST(c.dispositivo AS INTEGER) = d.id_dispositivo
""")
        consumo = cursor.fetchall()

        # Consulta para obter dispositivos
        cursor.execute("SELECT id_dispositivo, nome FROM Dispositivos")
        dispositivos = cursor.fetchall()

        cursor.close()
        conn.close()

        user_info['consumo'] = [(str(item[0]), item[1].strftime('%Y-%m-%d'), item[2].strftime('%H:%M:%S'), item[3], item[4], item[5], item[6], item[7]) for item in consumo]
        user_info['dispositivos'] = [(str(item[0]), item[1]) for item in dispositivos]

        return render_template('dashboard.html', user=user_info, dispositivos=dispositivos)
    return redirect(url_for('login'))

@app.route('/add_dispositivo', methods=['POST'])
def add_dispositivo():
    nome = request.form['nome']
    tipo = request.form['tipo']
    comodo = request.form['comodo']

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("INSERT INTO Dispositivos (nome, tipo, comodo) VALUES (%s, %s, %s)", 
                   (nome, tipo, comodo))
    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for('dashboard'))

@app.route('/add_consumo', methods=['POST'])
def add_consumo():
    data = request.form['data']
    hora = request.form['hora']
    quantidade = request.form['quantidade']
    recurso = request.form['recurso']
    dispositivo = request.form['dispositivo']

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("INSERT INTO Consumo (data, hora, quantidade, recurso, dispositivo) VALUES (%s, %s, %s, %s, %s)", 
                   (data, hora, quantidade, recurso, dispositivo))
    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for('dashboard'))

@app.route('/delete_consumo/<int:id>', methods=['POST'])
def delete_consumo(id):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM Consumo WHERE id_consumo = %s", (id,))
    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)

