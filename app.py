from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/api/hello', methods=['POST'])
def hello_world():
    response = jsonify({"message": "Hola mundo"})
    response.headers.add('Content-Type', 'application/json')
    return response

if __name__ == '__main__':
    app.run(port=5001, debug=True)
