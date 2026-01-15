import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Request, Depends, Form, Cookie, Response, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.services.chat_service import ChatService
# Importamos a classe Singleton criada anteriormente
from app.services.gemini_service import gemini_service 

router = APIRouter(prefix="/chat", tags=["chat"])
templates = Jinja2Templates(directory="app/templates")

# --- Dependências ---
async def get_chat_service(session: AsyncSession = Depends(get_session)) -> ChatService:
    return ChatService(session)

# Alias de tipo para deixar a assinatura das rotas mais limpa
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
SessionIdDep = Annotated[Optional[str], Cookie(alias="chat_session_id")]

# --- Rotas ---

@router.get("/widget", response_class=HTMLResponse)
async def chat_widget(request: Request):
    return templates.TemplateResponse("chat/widget.html", {"request": request})

@router.get("/window", response_class=HTMLResponse)
async def chat_window(
    request: Request,
    chat_service: ChatServiceDep,
    chat_session_id: SessionIdDep = None
):
    """
    Renderiza a janela. 
    Se não houver cookie, geramos o ID no Python, mas só setamos o cookie na resposta final.
    """
    # Se não tem sessão, gera um ID temporário para usar agora
    session_id = chat_session_id or str(uuid.uuid4())
    
    # Se o ID veio do cookie, buscamos histórico. Se é novo, lista vazia.
    history = []
    if chat_session_id:
        history = await chat_service.get_history(session_id)

    response = templates.TemplateResponse("chat/window.html", {
        "request": request,
        "history": history
    })

    # Se não tinha cookie antes, configura agora com segurança
    if not chat_session_id:
        response.set_cookie(
            key="chat_session_id",
            value=session_id,
            max_age=60 * 60 * 24 * 30, # 30 dias
            httponly=True, # Protege contra JavaScript malicioso
            samesite="lax" # Protege contra CSRF
        )

    return response

@router.post("/send", response_class=HTMLResponse)
async def send_message(
    request: Request,
    chat_service: ChatServiceDep,
    message: str = Form(...),
    chat_session_id: SessionIdDep = None
):
    """
    Passo 1: Salva msg do usuário e retorna HTML com gatilho HTMX.
    """
    if not message.strip():
        return Response(status_code=status.HTTP_200_OK)
    
    # Edge case: Usuário limpou cookies enquanto a janela estava aberta
    if not chat_session_id:
        # Retorna 400 para evitar criar sessões fantasmas sem cookie
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    # 1. Salva mensagem do usuário via Service
    user_msg = await chat_service.save_message(chat_session_id, "visitor", message)

    # 2. Retorna bolha com gatilho para buscar a resposta da IA
    return templates.TemplateResponse("chat/user_message_bubble.html", {
        "request": request,
        "message": user_msg
    })

@router.get("/get-ai-response", response_class=HTMLResponse)
async def get_ai_reply(
    request: Request,
    chat_service: ChatServiceDep,
    chat_session_id: SessionIdDep = None
):
    """
    Passo 2: Processamento Assíncrono da IA.
    """
    if not chat_session_id:
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    # 1. Busca contexto (Service de Chat)
    # Lembre-se: ChatService retorna do mais Antigo -> Novo
    history_objs = await chat_service.get_context_for_ai(chat_session_id)
    
    if not history_objs:
        return Response(content="Erro de contexto", status_code=500)

    # --- CORREÇÃO DE LÓGICA ---
    # A última mensagem do array é a que o usuário acabou de enviar.
    # Devemos usá-la como PROMPT e removê-la do HISTÓRICO para não duplicar.
    
    last_user_msg = history_objs[-1].message
    
    # O contexto para a IA deve ser tudo MENOS a última mensagem
    context_history = history_objs[:-1]

    # 2. Gera resposta (Service de IA - Singleton)
    ai_text = await gemini_service.get_response(last_user_msg, context_history)

    # 3. Salva resposta (Service de Chat)
    ai_msg = await chat_service.save_message(chat_session_id, "admin", ai_text)

    return templates.TemplateResponse("chat/ai_message_bubble.html", {
        "request": request,
        "message": ai_msg
    })