from flask import Flask, request, render_template, redirect, url_for, flash, session
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
import plotly.graph_objects as go

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

def alter_table_add_columns():
    conn = connect_db()
    cursor = conn.cursor()

    # Adicionar a coluna ID_user, se não existir
    cursor.execute("""
    ALTER TABLE Dispositivos
    ADD COLUMN IF NOT EXISTS ID_user INTEGER REFERENCES Usuarios(ID_user)
    """)

    # Adicionar a coluna status, se não existir
    cursor.execute("""
    ALTER TABLE Dispositivos
    ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'desligado'
    """)

    conn.commit()
    cursor.close()
    conn.close()

alter_table_add_columns()  # Chama a função para alterar a tabela quando o aplicativo inicializa

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM Usuarios WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user[3], password):  
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['email'] = user[2]

            # Iniciar dispositivos associados ao usuário
            cursor.execute("UPDATE Dispositivos SET status = 'iniciado' WHERE ID_user = %s", (user[0],))
            conn.commit()

            cursor.close()
            conn.close()

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
        user_id = session['user_id']

        conn = connect_db()
        cursor = conn.cursor()

        # Consulta para obter consumo e detalhes do dispositivo do usuário logado
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
        WHERE 
            d.ID_user = %s
        """, (user_id,))
        consumo = cursor.fetchall()

        # Consulta para obter dispositivos do usuário logado
        cursor.execute("SELECT id_dispositivo, nome FROM Dispositivos WHERE ID_user = %s", (user_id,))
        dispositivos = cursor.fetchall()

        # Dados Ideais
        dispositivos_ideais = {
            'Ar Condicionado': 46.1,  # kWh/mês
            'Chuveiro': 88,         # kWh/mês
            'Geladeira': 50,        # kWh/mês
            'Micro-ondas': 1.15 * 30,  # kWh/mês, assumindo 1.15 kWh por hora e 30 horas de uso
            'Televisão': 0.2 * 30,  # kWh/mês, assumindo 0.2 kWh por hora e 30 horas de uso
            'Lâmpada LED': 0.2 * 30  # kWh/mês, assumindo 0.2 kWh por hora e 30 horas de uso
        }

        # Preparar dados para gráficos
        user_consumo_dict = {}
        for item in consumo:
            dispositivo_nome = item[5]
            quantidade = item[3]
            if dispositivo_nome in user_consumo_dict:
                user_consumo_dict[dispositivo_nome] += quantidade
            else:
                user_consumo_dict[dispositivo_nome] = quantidade

        # Gráfico de Consumo do Usuário
        fig_consumo_usuario = go.Figure()
        fig_consumo_usuario.add_trace(go.Bar(
            x=list(user_consumo_dict.keys()),
            y=list(user_consumo_dict.values()),
            name='Consumo Real'
        ))

        fig_consumo_usuario.update_layout(
            title='Consumo Real por Dispositivo',
            xaxis_title='Dispositivo',
            yaxis_title='Consumo (kWh)'
        )

        # Gráfico de Comparação
        dispositivos_lista = list(dispositivos_ideais.keys())
        consumo_real = [user_consumo_dict.get(dev, 0) for dev in dispositivos_lista]
        consumo_ideal = [dispositivos_ideais.get(dev, 0) for dev in dispositivos_lista]

        fig_comparacao = go.Figure()
        fig_comparacao.add_trace(go.Bar(
            x=[dev for dev in dispositivos_lista],
            y=consumo_real,
            name='Consumo Real'
        ))

        fig_comparacao.add_trace(go.Bar(
            x=[dev for dev in dispositivos_lista],
            y=consumo_ideal,
            name='Consumo Ideal'
        ))

        fig_comparacao.update_layout(
            title='Comparação de Consumo Real e Ideal',
            xaxis_title='Dispositivo',
            yaxis_title='Consumo (kWh)',
            barmode='group'
        )

        # Gerar HTML para os gráficos
        plot_div = fig_consumo_usuario.to_html(full_html=False)
        plot_div_comparacao = fig_comparacao.to_html(full_html=False)

        cursor.close()
        conn.close()

        user_info['consumo'] = [(str(item[0]), item[1].strftime('%Y-%m-%d'), item[2].strftime('%H:%M:%S'), item[3], item[4], item[5], item[6], item[7]) for item in consumo]
        user_info['dispositivos'] = [(str(item[0]), item[1]) for item in dispositivos]

        # Verificar alertas
        alertas = []
        for dispositivo in dispositivos_lista:
            consumo_real_dispositivo = user_consumo_dict.get(dispositivo, 0)
            consumo_ideal_dispositivo = dispositivos_ideais.get(dispositivo, 0)
            if consumo_real_dispositivo > consumo_ideal_dispositivo:
                alertas.append(f"O dispositivo '{dispositivo}' está consumindo mais energia ({consumo_real_dispositivo} kWh) do que o ideal ({consumo_ideal_dispositivo} kWh).")

        return render_template('dashboard.html', user=user_info, dispositivos=dispositivos,
                               plot_div=plot_div, plot_div_comparacao=plot_div_comparacao, alertas=alertas)
    return redirect(url_for('login'))

@app.route('/add_dispositivo', methods=['POST'])
def add_dispositivo():
    nome = request.form['nome']
    tipo = request.form['tipo']
    comodo = request.form['comodo']
    user_id = session['user_id']

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("INSERT INTO Dispositivos (nome, tipo, comodo, ID_user) VALUES (%s, %s, %s, %s)", 
                   (nome, tipo, comodo, user_id))
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
    user_id = session['user_id']

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("INSERT INTO Consumo (data, hora, quantidade, recurso, dispositivo, ID_user) VALUES (%s, %s, %s, %s, %s, %s)", 
                   (data, hora, quantidade, recurso, dispositivo, user_id))
    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for('dashboard'))


@app.route('/delete_consumo/<int:id>', methods=['POST'])
def delete_consumo(id):
    user_id = session['user_id']
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM Consumo WHERE id_consumo = %s AND ID_user = %s", (id, user_id))
    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)



