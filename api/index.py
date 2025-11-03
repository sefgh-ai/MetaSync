from flask import Flask, send_from_directory, jsonify
import os

app = Flask(__name__, static_folder='..', static_url_path='')

@app.route('/')
def serve_index():
    return send_from_directory('..', 'index.html')

@app.route('/api/health')
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run()
