from flask import Flask, render_template, request, send_file, redirect, url_for, flash, session
import json
import csv
from io import StringIO, BytesIO
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Секретный ключ для сессий

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  role TEXT NOT NULL DEFAULT 'user')''')  # Добавляем поле role
    conn.commit()
    conn.close()

# Обновление базы данных (добавление поля 'role')
def update_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Проверяем, существует ли поле 'role'
    c.execute("PRAGMA table_info(users)")
    columns = c.fetchall()
    column_names = [column[1] for column in columns]
    
    if 'role' not in column_names:
        # Добавляем поле 'role'
        c.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
        conn.commit()
        print("Поле 'role' успешно добавлено в таблицу 'users'.")
    else:
        print("Поле 'role' уже существует в таблице 'users'.")
    
    conn.close()

# Регистрация пользователя
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form.get('role', 'user')  # По умолчанию роль 'user'

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, password, role))
            conn.commit()
            flash('Регистрация прошла успешно! Пожалуйста, войдите.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Пользователь с таким именем уже существует.')
        finally:
            conn.close()

    return render_template('register.html')

# Авторизация пользователя
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['username'] = username  # Сохраняем логин в сессии
            session['role'] = user[3]  # Сохраняем роль в сессии (user[3] — это поле role)
            print(f"Пользователь {username} вошел с ролью {user[3]}")  # Отладочный вывод
            return redirect(url_for('index'))
        else:
            flash('Неверный логин или пароль.')

    return render_template('login.html')

# Выход из системы
@app.route('/logout')
def logout():
    session.pop('username', None)  # Удаляем пользователя из сессии
    session.pop('role', None)  # Удаляем роль пользователя из сессии
    return redirect(url_for('index'))

# Главная страница
@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))  # Перенаправляем на страницу входа, если пользователь не авторизован

    print(f"Роль пользователя {session['username']}: {session.get('role')}")  # Отладочный вывод
    return render_template('index.html', role=session.get('role'))  # Передаем роль в шаблон

# Конвертер JSON в CSV (доступен только авторизованным пользователям)
@app.route('/convert', methods=['POST'])
def convert():
    if 'username' not in session:
        return redirect(url_for('login'))  # Перенаправляем на страницу входа, если пользователь не авторизован

    if 'file' not in request.files:
        return "Файл не загружен", 400

    file = request.files['file']
    if file.filename == '':
        return "Файл не выбран", 400

    if file and file.filename.endswith('.json'):
        try:
            # Чтение и парсинг JSON
            json_data = json.load(file)
        except json.JSONDecodeError as e:
            return f"Ошибка в формате JSON: {str(e)}", 400

        # Проверка, что JSON является списком словарей
        if not isinstance(json_data, list) or not all(isinstance(item, dict) for item in json_data):
            return "JSON должен быть списком словарей", 400

        # Преобразование JSON в CSV
        output = StringIO()
        writer = csv.writer(output)

        # Записываем заголовки (ключи)
        headers = json_data[0].keys()
        writer.writerow(headers)

        # Записываем значения
        for item in json_data:
            writer.writerow([item.get(header, "") for header in headers])

        # Преобразуем StringIO в байты
        output.seek(0)
        csv_bytes = BytesIO(output.getvalue().encode('utf-8'))

        # Возвращаем CSV файл для скачивания
        return send_file(
            csv_bytes,
            mimetype='text/csv',
            as_attachment=True,
            download_name='output.csv'
        )
    else:
        return "Неверный формат файла", 400

# Просмотр базы данных (доступен только администраторам)
@app.route('/view_db')
def view_db():
    if 'username' not in session:
        return redirect(url_for('login'))  # Только для авторизованных пользователей

    if session.get('role') != 'admin':
        flash('У вас нет прав для просмотра этой страницы.')
        return redirect(url_for('index'))

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    rows = c.fetchall()
    conn.close()

    return render_template('view_db.html', rows=rows)

if __name__ == '__main__':
    init_db()  # Инициализация базы данных при запуске приложения
    update_db()  # Обновление базы данных (добавление поля 'role')
    app.run(host='0.0.0.0', port=5000)