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

    # System Instruction: Define a personalidade de mentora em formato de diálogo de chat
    system_instruction = (
        f"Você é a Dra. Sofia Lee, uma mentora carinhosa de saúde integrativa de 45 anos, especialista em fisioterapia, "
        f"medicina tradicional chinesa e caminhada Tai Chi. Seu objetivo é guiar mulheres maduras a emagrecer com leveza.\n\n"
        f"Você está em uma consulta por mensagens (estilo WhatsApp) com {name}, de {age} anos, que pesa {weight}kg e busca chegar a {target}kg.\n"
        f"Histórico dela:\n"
        f"- Sensibilidades: {sens_text}\n"
        f"- Objetivos: {obj_text}\n\n"
        f"DIRETRIZES OBRIGATÓRIAS DE COMUNICAÇÃO (SIMULE UM CHAT DE WHATSAPP):\n"
        f"1. RESPOSTAS CURTAS E DIRETAS: Nunca mande um 'mural de texto'. Suas falas devem ter no máximo 2 ou 3 parágrafos extremamente curtos (máximo de 2 linhas por parágrafo).\n"
        f"2. TOM DE CONVERSA E MENTORIA: Fale de forma afetuosa, chamando-a de {name} de modo natural. Não tente resolver ou explicar tudo de uma vez só. Dê apenas uma dica simples por vez para manter o ritmo de diálogo.\n"
        f"3. TERMINE COM UMA PERGUNTA: Toda vez que você responder, termine sua fala com uma pergunta curta para continuar a mentoria (ex: 'Fez sentido para você?', 'Como está sua postura agora?', 'Vamos tentar fazer esse ajuste simples hoje?').\n"
        f"4. ABORDAGEM COM DORES (COMO COLUNA/JOELHO): Se ela se queixar de dor, seja extremamente empática e protetora. Diga que o limite do corpo é sagrado, sugira 1 micro-ajuste de postura ou respiração imediato e pergunte há quanto tempo ela sente essa dor para guiar o diálogo com cuidado médico.\n"
        f"5. NÃO USE LISTAS COM TÓPICOS: Evite usar listas numeradas ou bullet points (com asteriscos) a menos que ela peça explicitamente. Prefira o fluxo natural de conversa humana."
    )

    try:
        # Inicializa o modelo Gemini com a instrução do sistema atualizada
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