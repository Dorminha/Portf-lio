from sqlmodel import SQLModel, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
import os

# URL de conexão com o banco de dados.
# Em produção, isso deve vir de variáveis de ambiente.
# Exemplo para PostgreSQL: postgresql+asyncpg://user:password@localhost/dbname
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./database.db")

# Cria o engine assíncrono
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

async def init_db():
    """
    Inicializa o banco de dados, criando as tabelas se não existirem.
    """
    async with engine.begin() as conn:
        # await conn.run_sync(SQLModel.metadata.drop_all) # Descomente para resetar o DB
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session() -> AsyncSession:
    """
    Dependência para obter uma sessão assíncrona do banco de dados.
    """
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
