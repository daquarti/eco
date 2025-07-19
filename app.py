from flask import Flask, jsonify, request
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import os

# Cargar variables de entorno desde .env para desarrollo local
if os.path.exists('.env'):
    load_dotenv()

app = Flask(__name__)
CORS(app)

# Configurar OpenAI
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError('OPENAI_API_KEY environment variable is not set')

client = OpenAI(api_key=api_key)

@app.route('/api/hello', methods=['POST'])
def hello_world():
    response = jsonify({"message": "Hola mundo desde el backend en Render!"})
    response.headers.add('Content-Type', 'application/json')
    return response

@app.route('/api/analyze', methods=['POST'])
def analyze_text():
    try:
        data = request.json
        text = data.get('text', '')
        
        # Llamada a OpenAI
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Eres un asistente médico especializado en cardiología. Analiza el siguiente texto y proporciona un resumen conciso."},
                {"role": "user", "content": text}
            ]
        )
        
        analysis = completion.choices[0].message.content
        return jsonify({"analysis": analysis})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5001, debug=True)
