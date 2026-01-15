from google import genai
from google.genai import types
import logging
import asyncio
from typing import List
from app.core.config import get_settings

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

class GeminiService:
    _instance = None
    _client = None
    _model_name_cache = None

    def __new__(cls):
        """Implementação do padrão Singleton."""
        if cls._instance is None:
            cls._instance = super(GeminiService, cls).__new__(cls)
            cls._instance._configure()
        return cls._instance

    def _configure(self):
        """Configura a API key uma única vez."""
        if settings.GEMINI_API_KEY:
            try:
                self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
            except Exception as e:
                logger.error(f"Erro fatal config Gemini: {e}")

    def _get_best_model_name(self) -> str:
        """
        Busca o modelo apenas UMA VEZ e salva em memória (Cache).
        """
        if self._model_name_cache:
            return self._model_name_cache

        logger.info("Detectando melhor modelo Gemini disponível...")
        
        # Lista de preferência (nomes de modelos atualizados para genai)
        priorities = [
            'gemini-2.0-flash', 
            'gemini-1.5-flash', 
            'gemini-1.5-pro',
            'gemini-pro'
        ]

        try:
           # Tentativa de listar (se suportado pelo cliente de forma simples)
           # Caso contrário, fallback direto.
           # self._client.models.list() retorna iterador de Model.
           # Vamos apenas assumir o fallback para simplificar e performance.
           pass
        except Exception:
            pass
            
        # Fallback seguro
        fallback = 'gemini-1.5-flash'
        self._model_name_cache = fallback
        return fallback

    async def get_response(self, user_message: str, history_objs: list) -> str:
        """Método público para gerar respostas."""
        if not self._client:
            return "⚠️ Erro: Chave de API não configurada no servidor."

        try:
            model_name = self._get_best_model_name()
            
            # System Instruction (Persona)
            system_instruction = (
                "Você é a Persona Digital de Luan de Paz, um Engenheiro de Software e RPA. "
                "Sua stack principal é Python, FastAPI e React. "
                "Responda sempre em Português do Brasil. "
                "Seja técnico, porém amigável e conciso."
            )

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
                temperature=0.4,
                max_output_tokens=500,
                system_instruction=system_instruction,
                safety_settings=safety_settings
            )

            # Constrói o histórico no formato Gemini
            gemini_history = []
            for msg in history_objs:
                # Ignora mensagens vazias
                if not msg.message or not msg.message.strip():
                    continue
                
                role = 'user' if msg.sender == 'visitor' else 'model'
                gemini_history.append(types.Content(role=role, parts=[types.Part.from_text(text=msg.message)]))

            # Inicia o chat e envia mensagem
            chat = self._client.aio.chats.create(
                model=model_name,
                config=config,
                history=gemini_history
            )
            
            response = await chat.send_message(user_message)
            return response.text

        except Exception as e:
            # 1. Retry Logic for 429 (Rate Limit) or 503 (Overloaded)
            if "429" in str(e) or "503" in str(e):
                logger.warning(f"⚠️ Rate Limit/Overload detectado: {e}. Tentando novamente em 2s...")
                try:
                    await asyncio.sleep(2)
                    chat = self._client.aio.chats.create(
                        model=model_name,
                        config=config,
                        history=gemini_history
                    )
                    response = await chat.send_message(user_message)
                    return response.text
                except Exception as retry_e:
                    logger.error(f"❌ Retry falhou. Erro final: {retry_e}")
                    # Log full error for debugging paid tier issues
                    logger.error(f"Full Error Details: {type(retry_e).__name__} - {retry_e}")
                    
                    if "429" in str(retry_e):
                        return "Muitas requisições (Quota Excedida). Tente novamente em alguns segundos."

            logger.error(f"ERRO GEMINI: {str(e)}")
            return "Desculpe, estou passando por uma manutenção momentânea."

# Instância Global exportada
gemini_service = GeminiService()