# Arquivo: app/services/chat_service.py

from typing import List
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models import ChatMessage

class ChatService:
    def __init__(self, session: AsyncSession):
        """
        Injeta a sessão do banco de dados na classe.
        """
        self.session = session

    async def get_history(self, session_id: str, limit: int = 20) -> List[ChatMessage]:
        """
        Busca o histórico de mensagens de uma sessão específica.
        Retorna na ordem cronológica (Antigo -> Novo) para exibição correta no chat.
        """
        statement = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.timestamp.desc()) # Pega os mais recentes primeiro
            .limit(limit)
        )
        result = await self.session.exec(statement)
        messages = result.all()
        
        # Inverte a lista para que a mensagem mais antiga fique no topo da janela de chat
        return messages[::-1]

    async def get_context_for_ai(self, session_id: str, limit: int = 6) -> List[ChatMessage]:
        """
        Busca um histórico curto apenas para dar contexto à Inteligência Artificial.
        Reutiliza a lógica do get_history.
        """
        return await self.get_history(session_id, limit)

    async def save_message(self, session_id: str, sender: str, content: str) -> ChatMessage:
        """
        Salva uma nova mensagem no banco de dados.
        """
        new_msg = ChatMessage(
            session_id=session_id,
            sender=sender,
            message=content
        )
        
        self.session.add(new_msg)
        await self.session.commit()
        await self.session.refresh(new_msg)
        
        return new_msg