from google import genai
from google.genai import types
import logging
from typing import List, Optional
from app.core.config import get_settings

# Configura apenas o logger local, sem mexer na config global do app
logger = logging.getLogger(__name__)
settings = get_settings()

# ==========================================
# CONSTANTES & PROMPTS (Separação de Dados)
# ==========================================
# Definir o prompt aqui ou em um arquivo separado (app/core/prompts.py)
SYSTEM_INSTRUCTION = """
Você é a Persona Digital de Luan de Paz, um Engenheiro de Software e RPA.
Sua stack principal é Python, FastAPI e React.
Responda sempre em Português do Brasil.
Seja técnico, porém amigável, conciso e direto ao ponto.
Não invente projetos que não existem no histórico fornecido.
Se não souber algo, diga que não tem essa informação no momento.
"""

# Modelo padrão: O Flash é o mais rápido e eficiente para Chatbots de Portfólio
# Atualizando para nome de modelo compatível se necessário, mas geralmente ids são mantidos.
DEFAULT_MODEL = "gemini-1.5-flash"

class GeminiService:
    """
    Serviço Singleton para interação com Google Gemini.
    Mantém o cliente configurado e pronto para uso.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GeminiService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        # Garante que a configuração rode apenas uma vez
        if self._initialized:
            return
            
        self._client = None
        self._setup_client()
        self._initialized = True

    def _setup_client(self):
        """Configura a API Key e prepara a instância do Modelo."""
        if not settings.GEMINI_API_KEY:
            logger.warning("Gemini API Key não encontrada. O chat não funcionará.")
            return

        try:
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
            logger.info(f"Gemini Service inicializado com modelo: {DEFAULT_MODEL}")

        except Exception as e:
            logger.error(f"Falha ao configurar Gemini: {e}")
            self._client = None

    async def get_response(self, user_message: str, history_objs: list) -> str:
        """
        Gera resposta baseada na mensagem atual e no histórico do banco.
        """
        if not self._client:
            return "⚠️ Erro: O serviço de IA não está configurado corretamente (Verifique a API Key)."

        try:
            # Configurações de Segurança
            safety_settings = [
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH
                ),
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH
                ),
            ]

            # Configuração de Geração
            config = types.GenerateContentConfig(
                temperature=0.4, # Criatividade controlada
                max_output_tokens=500,
                system_instruction=SYSTEM_INSTRUCTION,
                safety_settings=safety_settings
            )

            # 1. Converte histórico do banco (SQLModel) para o formato do Gemini
            chat_history = []
            for msg in history_objs:
                if not msg.message or not msg.message.strip():
                    continue
                
                role = 'user' if msg.sender == 'visitor' else 'model'
                chat_history.append(types.Content(role=role, parts=[types.Part.from_text(text=msg.message)]))

            # 2. Inicia uma sessão de chat (Stateless para o servidor, Stateful para o LLM)
            # O histórico é enviado a cada requisição, o que é padrão para APIs REST.
            chat_session = self._client.aio.chats.create(
                model=DEFAULT_MODEL,
                config=config,
                history=chat_history
            )
            
            # 3. Envia a mensagem (Assíncrono)
            response = await chat_session.send_message(user_message)
            return response.text

        except Exception as e:
            logger.exception("Erro durante a geração de resposta do Gemini")
            
            # Tratamento de erro amigável para o usuário
            error_str = str(e)
            if "429" in error_str:
                return "Estou recebendo muitas mensagens agora. Tente novamente em alguns segundos. inhaler"
            if "403" in error_str or "API_KEY" in error_str:
                return "Erro de configuração na minha chave de acesso."
            
            return "Desculpe, tive um problema técnico momentâneo. Tente perguntar de outra forma."

# Instância Global (Padrão Singleton via Módulo Python)
gemini_service = GeminiService()