from typing import Optional
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel

# Função auxiliar para substituir datetime.utcnow (que está depreciado)
def get_now_utc():
    return datetime.now(timezone.utc)

class Project(SQLModel, table=True):
    """
    Modelo de dados para os projetos do portfólio.
    """
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    url: str
    stars: int = Field(default=0)
    language: Optional[str] = None
    
    # ADICIONADO: Para salvar o README em cache e não depender do GitHub a todo momento
    readme_content: Optional[str] = None 
    
    # Atualizado para timezone aware
    created_at: datetime = Field(default_factory=get_now_utc)
    updated_at: datetime = Field(default_factory=get_now_utc)

    # --- MÉTODOS AUXILIARES ---
    @property
    def repo_slug(self) -> str:
        if self.url:
            return self.url.rstrip("/").split("/")[-1]
        return self.name 

    @property
    def repo_owner(self) -> str:
        if self.url and "github.com" in self.url:
            parts = self.url.rstrip("/").split("/")
            if len(parts) >= 2:
                return parts[-2]
        return "Dorminha"

class ContactMessage(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str
    message: str
    sent_at: datetime = Field(default_factory=get_now_utc)

class Article(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    slug: str = Field(unique=True)
    content: str
    summary: str
    published_at: datetime = Field(default_factory=get_now_utc)
    is_published: bool = Field(default=False)

class ChatMessage(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # --- OBRIGATÓRIO PARA O CHAT FUNCIONAR ---
    # Identifica de quem é a conversa (Cookies)
    session_id: str = Field(index=True) 
    # -----------------------------------------

    sender: str  # "visitor" or "admin"
    message: str
    timestamp: datetime = Field(default_factory=get_now_utc)
    is_read: bool = Field(default=False)