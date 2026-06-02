import os
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

    @app.route('/upsell')
def upsell():
    return render_template('upsell.html')

if __name__ == '__main__':
    # O Railway define a porta automaticamente através da variável de ambiente PORT
    # Se ele não encontrar a variável (como no seu computador), ele usa a 8080 por padrão
    port = int(os.environ.get("PORT", 8080))
    
    # Importante: host='0.0.0.0' permite que o Railway torne seu app público
    app.run(host='0.0.0.0', port=port)
