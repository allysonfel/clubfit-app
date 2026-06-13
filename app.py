import os
import sqlite3
import hashlib
import random
import string
import json
import urllib.request
from flask import Flask, render_template, request, jsonify, session

app = Flask(__name__)

# Configuração de Segurança de Sessão (Necessária para proteger os cookies de login)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "chave_secreta_padrao_muito_segura_123")

# Configuração do Gemini AI
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)

# Configuração do Caminho do Banco de Dados SQLite (Persistência no Volume do Railway)
DB_PATH = "/data/clubfit.db"
if not os.path.exists("/data"):
    # Fallback local de desenvolvimento caso a pasta /data não exista
    DB_PATH = "clubfit.db"

# ── INICIALIZADOR DO BANCO DE DADOS (Executa automaticamente no deploy) ──
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Criar tabela de usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            status TEXT DEFAULT 'pending_payment',
            is_vip INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Criar tabela de métricas ligada aos usuários (incluindo persistência de progresso pessoal)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metrics (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            age INTEGER,
            height INTEGER,
            weight REAL,
            target_weight REAL,
            sensibilidades TEXT,
            objetivos TEXT,
            completed_days TEXT DEFAULT '',
            streak INTEGER DEFAULT 0,
            water_drunk INTEGER DEFAULT 0,
            weight_history TEXT DEFAULT '',
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Executa migrações silenciosas para garantir que novos campos existam em bancos de dados já criados
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_vip INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute("ALTER TABLE metrics ADD COLUMN completed_days TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute("ALTER TABLE metrics ADD COLUMN streak INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute("ALTER TABLE metrics ADD COLUMN water_drunk INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute("ALTER TABLE metrics ADD COLUMN weight_history TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
        
    conn.commit()
    conn.close()

# Inicializa o banco de dados
init_db()

# ── ENVIADOR DE E-MAIL COM RESEND (Nativo, sem pacotes adicionais) ──
def send_welcome_email(email, password):
    resend_api_key = os.environ.get("RESEND_API_KEY")
    if not resend_api_key:
        print("AVISO: RESEND_API_KEY não configurada nas variáveis do Railway.")
        return False
        
    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {resend_api_key}",
        "Content-Type": "application/json"
    }
    
    html_content = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eaeaea; border-radius: 12px; background: #fff;">
        <h2 style="color: #2E9E58; text-align: center; font-weight: 800;">Seu acesso ao ClubFit está liberado! 🎉</h2>
        <p>Olá, amiga! Seu pagamento foi confirmado com sucesso e sua conta na nossa área de membros já está ativa.</p>
        <p>Abaixo estão suas credenciais exclusivas para acessar o aplicativo:</p>
        
        <div style="background: #f5f5f0; padding: 16px; border-radius: 8px; margin: 20px 0; font-size: 15px; border-left: 4px solid #2E9E58;">
            <strong>E-mail de acesso:</strong> {email}<br>
            <strong>Senha temporária:</strong> {password}
        </div>
        
        <p>Por questões de segurança, recomendamos que altere a sua senha dentro do seu perfil assim que realizar o seu primeiro login.</p>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="https://clubfit.online/app" style="background: #2E9E58; color: #fff; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">Acessar Área de Membros</a>
        </div>
        
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
        <p style="font-size: 11px; color: #999; text-align: center;">Smart Produtos Digitais LTDA • ClubFit © 2026</p>
    </div>
    """
    
    payload = {
        "from": "ClubFit <suporte@clubfit.online>", # Certifique-se de que clubfit.online está verificado no Resend
        "to": [email],
        "subject": "Seu acesso ao ClubFit está liberado!",
        "html": html_content
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode('utf-8')
            print("E-mail de acesso enviado via Resend com sucesso:", res_body)
            return True
    except Exception as e:
        print("Erro ao tentar enviar e-mail via Resend:", str(e))
        return False


# ── ROTAS DE PÁGINAS DO FUNIL ──

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upsell')
def upsell():
    return render_template('upsell.html')

@app.route('/app')
def app_member():
    return render_template('app.html')

@app.route('/login')
def login_page():
    return render_template('login.html')


# ── ROTAS DE INTEGRAÇÃO DE SESSÃO E DADOS (API) ──

# 1. Salva os dados do Quiz em segundo plano quando coloca o E-mail (Step 34)
@app.route('/api/salvar-quiz', methods=['POST'])
def salvar_quiz():
    data = request.get_json() or {}
    email = data.get("email", "").lower().strip()
    user_data = data.get("userData", {})
    
    if not email:
        return jsonify({"error": "E-mail é obrigatório"}), 400
        
    name = user_data.get("name", "amiga")
    weight = user_data.get("weight", 70)
    target_weight = user_data.get("targetWeight", 60)
    age = user_data.get("age", 35)
    height = user_data.get("height", 170)
    
    sensibilidades = user_data.get("sensibilidades", [])
    sens_str = ",".join(sensibilidades) if isinstance(sensibilidades, list) else str(sensibilidades)
    
    objetivos = user_data.get("objetivos", [])
    obj_str = ",".join(objetivos) if isinstance(objetivos, list) else str(objetivos)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Verifica se o e-mail já existe
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if user:
            user_id = user[0]
        else:
            # Cria um usuário temporário 'pendente de pagamento' com hash placeholder
            placeholder_pw = hashlib.sha256("placeholder_temporary_key".encode()).hexdigest()
            cursor.execute("INSERT INTO users (email, password, status) VALUES (?, ?, 'pending_payment')", (email, placeholder_pw))
            user_id = cursor.lastrowid
            
        # Salva ou atualiza as métricas associadas ao ID do usuário
        cursor.execute("SELECT user_id FROM metrics WHERE user_id = ?", (user_id,))
        if cursor.fetchone():
            cursor.execute('''
                UPDATE metrics 
                SET name = ?, age = ?, height = ?, weight = ?, target_weight = ?, sensibilidades = ?, objetivos = ?
                WHERE user_id = ?
            ''', (name, age, height, weight, target_weight, sens_str, obj_str, user_id))
        else:
            cursor.execute('''
                INSERT INTO metrics (user_id, name, age, height, weight, target_weight, sensibilidades, objetivos)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, name, age, height, weight, target_weight, sens_str, obj_str))
            
        conn.commit()
        return jsonify({"success": True}), 200
    except Exception as e:
        print("Erro ao tentar salvar os dados do quiz:", str(e))
        return jsonify({"error": "Falha interna ao processar os dados do quiz."}), 500
    finally:
        conn.close()

# 2. Recebe a aprovação do pagamento da Cakto Pay, gera acesso e dispara o e-mail
@app.route('/api/webhook', methods=['POST'])
def cakto_webhook():
    data = request.get_json() or {}
    print("Webhook Cakto recebido:", data)
    
    event = data.get("event")
    status = data.get("status")
    
    # Processa se o evento for de aprovação/conclusão de pagamento
    if event == "purchase_approved" or status in ["approved", "paid"]:
        customer_data = data.get("data", {}).get("customer", {})
        email = customer_data.get("email") if customer_data else None
        
        if not email:
            email = data.get("email") or data.get("customer", {}).get("email")
            
        if not email:
            return jsonify({"error": "E-mail do comprador não encontrado"}), 400
            
        email = email.lower().strip()
        
        temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        hashed_password = hashlib.sha256(temp_password.encode()).hexdigest()
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            
            # Se for uma aprovação de plano VIP, altera o is_vip para 1
            is_upsell = "vip" in str(data.get("data", {}).get("items", [{}])[0].get("title", "")).lower()
            
            if user:
                user_id = user[0]
                if is_upsell:
                    cursor.execute("UPDATE users SET is_vip = 1 WHERE id = ?", (user_id,))
                else:
                    cursor.execute("UPDATE users SET password = ?, status = 'active' WHERE id = ?", (hashed_password, user_id))
            else:
                is_vip_val = 1 if is_upsell else 0
                cursor.execute("INSERT INTO users (email, password, status, is_vip) VALUES (?, ?, 'active', ?)", (email, hashed_password, is_vip_val))
                user_id = cursor.lastrowid
                
                customer_name = customer_data.get("name", "Amiga")
                cursor.execute("INSERT INTO metrics (user_id, name, age, height, weight, target_weight) VALUES (?, ?, 35, 170, 70.0, 60.0)", (user_id, customer_name))
                
            conn.commit()
            
            # Envia e-mail de boas-vindas com as credenciais se não for apenas o upsell de VIP
            if not is_upsell:
                send_welcome_email(email, temp_password)
                
            return jsonify({"success": True, "message": "Acesso criado e e-mail enviado."}), 200
        except Exception as e:
            print("Erro ao ativar conta via Webhook:", str(e))
            return jsonify({"error": str(e)}), 500
        finally:
            conn.close()
            
    return jsonify({"message": "Evento ignorado (não aprovado)"}), 200

# 3. Executa o Login de Usuários na Área de Membros
@app.route('/api/login', methods=['POST'])
def login_api():
    data = request.get_json() or {}
    email = data.get("email", "").lower().strip()
    password = data.get("password", "")
    
    if not email or not password:
        return jsonify({"error": "Por favor, preencha todos os campos."}), 400
        
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, status FROM users WHERE email = ? AND password = ?", (email, hashed_password))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return jsonify({"error": "E-mail ou senha incorretos."}), 401
        
    user_id, status = user
    
    if status != "active":
        return jsonify({"error": "Seu acesso ainda está aguardando confirmação de pagamento."}), 403
        
    session['user_id'] = user_id
    session['email'] = email
    
    return jsonify({"success": True}), 200

# 4. Finaliza a Sessão de Login (Sair)
@app.route('/api/logout', methods=['POST', 'GET'])
def logout_api():
    session.clear()
    return jsonify({"success": True}), 200

# 5. Fornece os dados do usuário para o app.html de forma dinâmica
@app.route('/api/user/data', methods=['GET'])
def get_user_data():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Não autorizado"}), 401
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT email, is_vip FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    
    cursor.execute('''
        SELECT name, age, height, weight, target_weight, sensibilidades, objetivos,
               completed_days, streak, water_drunk, weight_history
        FROM metrics WHERE user_id = ?
    ''', (user_id,))
    metrics = cursor.fetchone()
    conn.close()
    
    if not user:
        return jsonify({"error": "Usuário inválido"}), 404
        
    email, is_vip = user
    
    if metrics:
        name, age, height, weight, target_weight, sens, obj, comp_days, streak, water, weight_hist = metrics
        sens_list = sens.split(",") if sens else []
        obj_list = obj.split(",") if obj else []
        comp_days_list = [int(d) for d in comp_days.split(",") if d] if comp_days else []
        weight_hist_list = [float(w) for w in weight_hist.split(",") if w] if weight_hist else [weight]
    else:
        name, age, height, weight, target_weight, sens_list, obj_list = ("amiga", 35, 170, 70.0, 60.0, [], [])
        comp_days_list, streak, water, weight_hist_list = ([], 0, 0, [70.0])
        
    return jsonify({
        "email": email,
        "isVipSubscribed": is_vip == 1,
        "userData": {
            "name": name,
            "age": age,
            "height": height,
            "weight": weight,
            "targetWeight": target_weight,
            "sensibilidades": sens_list,
            "objetivos": obj_list
        },
        "appState": {
            "completedDays": comp_days_list,
            "streak": streak,
            "waterDrunk": water,
            "weightHistory": weight_hist_list
        }
    }), 200

# 6. Atualiza Progresso (Constância, Água e Peso) no Banco de Dados
@app.route('/api/user/progress', methods=['POST'])
def update_user_progress():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Não autorizado"}), 401
        
    data = request.get_json() or {}
    completed_days = data.get("completedDays", [])
    streak = data.get("streak", 0)
    water_drunk = data.get("waterDrunk", 0)
    weight_history = data.get("weightHistory", [])
    
    # Converte as listas do frontend para o formato texto do SQLite
    comp_days_str = ",".join(str(d) for d in completed_days) if isinstance(completed_days, list) else ""
    weight_hist_str = ",".join(str(w) for w in weight_history) if isinstance(weight_history, list) else ""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE metrics 
            SET completed_days = ?, streak = ?, water_drunk = ?, weight_history = ?
            WHERE user_id = ?
        ''', (comp_days_str, streak, water_drunk, weight_hist_str, user_id))
        conn.commit()
        return jsonify({"success": True}), 200
    except Exception as e:
        print("Erro ao tentar salvar progresso de treino:", str(e))
        return jsonify({"error": "Erro interno ao salvar progresso."}), 500
    finally:
        conn.close()

# 7. Atualiza Métricas ou altera a senha de dentro do app.html
@app.route('/api/user/update', methods=['POST'])
def update_user_data():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Não autorizado"}), 401
        
    data = request.get_json() or {}
    user_data = data.get("userData", {})
    new_password = data.get("password", "").strip()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Atualiza a senha do usuário se preenchida
        if new_password:
            if len(new_password) < 6:
                return jsonify({"error": "A senha deve ter no mínimo 6 caracteres."}), 400
            hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
            cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed_password, user_id))
            
        # Atualiza métricas e dados de saúde
        name = user_data.get("name", "amiga")
        age = user_data.get("age", 35)
        height = user_data.get("height", 170)
        weight = user_data.get("weight", 70.0)
        target_weight = user_data.get("targetWeight", 60.0)
        
        sens = user_data.get("sensibilidades", [])
        sens_str = ",".join(sens) if isinstance(sens, list) else str(sens)
        
        obj = user_data.get("objetivos", [])
        obj_str = ",".join(obj) if isinstance(obj, list) else str(obj)
        
        cursor.execute('''
            UPDATE metrics 
            SET name = ?, age = ?, height = ?, weight = ?, target_weight = ?, sensibilidades = ?, objetivos = ?
            WHERE user_id = ?
        ''', (name, age, height, weight, target_weight, sens_str, obj_str, user_id))
        
        conn.commit()
        return jsonify({"success": True}), 200
    except Exception as e:
        print("Erro ao tentar atualizar métricas do usuário:", str(e))
        return jsonify({"error": "Erro interno ao atualizar os dados."}), 500
    finally:
        conn.close()

# 8. Consulta a Dra. Sofia Lee associada ao login do banco de dados (Sincronizado)
@app.route('/api/chat', methods=['POST'])
def chat_with_sofia():
    if not GEMINI_API_KEY:
        return jsonify({"error": "Chave de API do Gemini não configurada no servidor."}), 500
        
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Não autorizado"}), 401
        
    data = request.get_json() or {}
    user_message = data.get("message", "").strip()
    
    if not user_message:
        return jsonify({"error": "Mensagem vazia."}), 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT name, age, height, weight, target_weight, sensibilidades, objetivos 
        FROM metrics WHERE user_id = ?
    ''', (user_id,))
    metrics = cursor.fetchone()
    conn.close()

    if metrics:
        name, age, height, weight, target_weight, sens_str, obj_str = metrics
    else:
        name, age, height, weight, target_weight, sens_str, obj_str = ("amiga", 35, 170, 70.0, 60.0, "Nenhuma", "Emagrecer")

    system_instruction = (
        f"Você é a Dra. Sofia Lee, uma mentora carinhosa de saúde integrativa de 45 anos, especialista em fisioterapia, "
        f"medicina tradicional chinesa e caminhada Tai Chi. Seu objetivo é guiar mulheres maduras a emagrecer com leveza.\n\n"
        f"Você está em uma consulta por mensagens (estilo WhatsApp) com {name}, de {age} anos, que pesa {weight}kg e busca chegar a {target_weight}kg.\n"
        f"Histórico dela:\n"
        f"- Sensibilidades: {sens_str}\n"
        f"- Objetivos: {obj_str}\n\n"
        f"DIRETRIZES OBRIGATÓRIAS DE COMUNICAÇÃO (SIMULE UM CHAT DE WHATSAPP REAL):\n"
        f"1. RESPOSTAS CURTAS E DIRETAS: Nunca mande um 'mural de texto'. Suas falas devem ter no máximo 2 ou 3 parágrafos extremamente curtos (máximo de 2 linhas por parágrafo).\n"
        f"2. SEM SAUDAÇÕES REPETITIVAS: Como esta é uma conversa contínua por chat, NUNCA comece suas respostas com 'Oi', 'Olá', 'Oi, amiga', 'Oi, querida' ou 'Como vai?'. O oi já foi dado na primeira mensagem. Comece respondendo diretamente ao que ela falou para parecer um diálogo humano e fluido.\n"
        f"3. TOM DE CONVERSA E MENTORIA: Fale de forma afetuosa e empática, usando o nome dela ({name}) de modo natural. Não tente explicar tudo de uma vez só. Dê apenas uma dica simples por vez para manter o fluxo de conversa.\n"
        f"4. TERMINE COM UMA PERGUNTA: Toda vez que você responder, termine sua fala com uma pergunta curta para continuar a mentoria de forma suave (ex: 'Fez sentido para você?', 'Como está sua postura agora?', 'Vamos tentar fazer esse ajuste simples hoje?').\n"
        f"5. LIMITAÇÕES E ADAPTAÇÕES DE TAI CHI: Se ela relatar dificuldades físicas (como estar acima do peso, falta de equilíbrio ou dores), use seu conhecimento em Tai Chi para sugerir adaptações seguras imediatas (como realizar o movimento sentada em uma cadeira firme, reduzir a amplitude do passo, ou focar puramente na respiração abdominal profunda e na transferência suave de peso). Diga que o limite do corpo dela é sagrado.\n"
        f"6. NÃO USE LISTAS COM TÓPICOS: Evite usar listas numeradas ou bullet points (com asteriscos) a menos que ela peça explicitamente. Prefira o fluxo natural de conversa humana."
    )

    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=system_instruction
        )
        response = model.generate_content(user_message)
        
        if response and response.text:
            return jsonify({"response": response.text})
        else:
            return jsonify({"response": "Tive um pequeno probleminha para formular essa resposta agora, querida. Poderia me perguntar de outra forma?"})
        
    except Exception as e:
        print(f"Erro ao processar com o Gemini: {str(e)}")
        return jsonify({"error": "Erro interno do servidor ao consultar a inteligência artificial."}), 500

# ── ROTA TEMPORÁRIA: Cria usuário de testes ativo no banco para testes rápidos ──
@app.route('/api/criar-teste')
def criar_usuario_teste():
    import hashlib
    email_teste = "teste@clubfit.online"
    senha_teste = "senha123"
    hashed_senha = hashlib.sha256(senha_teste.encode()).hexdigest()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # Insere ou substitui o usuário de testes ativo
        cursor.execute('''
            INSERT OR REPLACE INTO users (id, email, password, status) 
            VALUES (999, ?, ?, 'active')
        ''', (email_teste, hashed_senha))
        
        # Insere as métricas de saúde iniciais para o teste
        cursor.execute('''
            INSERT OR REPLACE INTO metrics (user_id, name, age, height, weight, target_weight, sensibilidades, objetivos, completed_days, streak, water_drunk, weight_history) 
            VALUES (999, 'Mariana Rezende', 45, 168, 82.5, 68.0, 'Joelhos sensíveis', 'Perder peso, Reduzir idade biológica', '', 0, 0, '82.5')
        ''')
        
        conn.commit()
        return "<h3>Usuário de testes criado com sucesso!</h3><p>Acesse seu app e faça login com:<br><b>E-mail:</b> teste@clubfit.online<br><b>Senha:</b> senha123</p>"
    except Exception as e:
        print("Erro ao criar usuário de teste:", str(e))
        return f"Erro ao criar usuário: {str(e)}"
    finally:
        conn.close()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)