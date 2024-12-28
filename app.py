from flask import Flask, render_template, request, send_file
import json
import csv
from io import StringIO, BytesIO

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)