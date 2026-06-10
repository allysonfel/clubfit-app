import os
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# Configuração de Segurança: Lê de forma oculta da variável de ambiente do Railway
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upsell')
def upsell():
    return render_template('upsell.html')

@app.route('/app')
def app_member():
    return render_template('app.html')

# ROTA: Processa as mensagens com inteligência dinâmica real usando o Gemini 2.5 Flash
@app.route('/api/chat', methods=['POST'])
def chat_with_sofia():
    if not GEMINI_API_KEY:
        return jsonify({"error": "Chave de API do Gemini não configurada no servidor."}), 500
    
    data = request.get_json() or {}
    user_message = data.get("message", "").strip()
    
    # Previne erros caso 'userData' venha explicitamente como null/None no JSON
    user_data = data.get("userData") or {}
    
    if not user_message:
        return jsonify({"error": "Mensagem vazia."}), 400

    # Extrai as informações de perfil do Quiz
    name = user_data.get("name", "amiga")
    if not name or name.lower() in ["você", "voce", ""]:
        name = "amiga"
    
    weight = user_data.get("weight", "70")
    target = user_data.get("targetWeight", "60")
    age = user_data.get("age", "35")
    sensibilidades = user_data.get("sensibilidades", [])
    objetivos = user_data.get("objetivos", [])

    # Tratamento seguro contra o bug do .join() caso os dados venham como string corrida
    if isinstance(sensibilidades, str):
        sens_text = sensibilidades if sensibilidades.strip() else "Nenhuma sensibilidade marcada"
    elif isinstance(sensibilidades, list):
        sens_text = ", ".join(str(s) for s in sensibilidades) if sensibilidades else "Nenhuma sensibilidade marcada"
    else:
        sens_text = "Nenhuma sensibilidade marcada"

    if isinstance(objetivos, str):
        obj_text = objetivos if objetivos.strip() else "Emagrecer de forma saudável"
    elif isinstance(objetivos, list):
        obj_text = ", ".join(str(o) for o in objetivos) if objetivos else "Emagrecer de forma saudável"
    else:
        obj_text = "Emagrecer de forma saudável"

    # System Instruction: Define a personalidade e injeta o perfil de saúde do usuário na IA
    system_instruction = (
        f"Você é a Dra. Sofia Lee, uma mentora de saúde integrativa e especialista em medicina tradicional "
        f"chinesa e caminhada Tai Chi em casa. Seu tom de voz é acolhedor, empático, carinhoso, extremamente profissional e focado "
        f"em motivar mulheres mais maduras a resgatar a saúde e emagrecer de forma leve e sem sofrimento.\n\n"
        f"Você está conversando com a {name}, que tem {age} anos, pesa {weight}kg atualmente, e tem como objetivo "
        f"alcançar {target}kg.\n"
        f"As sensibilidades físicas marcadas por ela no quiz são: {sens_text}.\n"
        f"Os objetivos principais dela são: {obj_text}.\n\n"
        f"Instruções importantes para suas respostas:\n"
        f"1. Responda sempre de forma curta e amigável (máximo 2 a 3 parágrafos curtos), imitando o ritmo de conversa rápida de chat.\n"
        f"2. Use o nome dela ({name}) de forma carinhosa e natural durante a conversa.\n"
        f"3. Utilize o histórico e as dores dela para orientar de forma personalizada e segura sempre que ela perguntar sobre exercícios, posições ou desconfortos.\n"
        f"4. Traga dicas reais, científicas e baseadas nas técnicas de respiração do Tai Chi e hábitos saudáveis."
    )

    try:
        # Inicializa o modelo Gemini com a instrução do sistema (usando o modelo atualizado gemini-2.5-flash)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=system_instruction
        )
        
        response = model.generate_content(user_message)
        
        # Validação de segurança: caso os filtros do Gemini bloqueiem o conteúdo gerado
        if response and response.text:
            return jsonify({"response": response.text})
        else:
            return jsonify({"response": "Desculpe, querida. Tive um probleminha para formular essa resposta agora. Pode me perguntar de outra forma?"})
        
    except Exception as e:
        # Registra o erro internamente nos logs do servidor (útil para debugar no Railway)
        print(f"Erro ao processar com o Gemini: {str(e)}")
        return jsonify({"error": f"Erro interno do servidor ao consultar a inteligência artificial."}), 500

if __name__ == '__main__':
    # O Railway define a porta automaticamente através da variável de ambiente PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)