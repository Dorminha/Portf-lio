import secrets
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Configurações da aplicação.
    Os valores são lidos de variáveis de ambiente ou do arquivo .env.
    """
    
    # ==========================================
    # Configurações Gerais
    # ==========================================
    APP_NAME: str = "DevFolio"
    # Segurança por padrão: Debug deve ser False em produção
    DEBUG: bool = False
    
    # ==========================================
    # Segurança & Autenticação
    # ==========================================
    # ATENÇÃO: Nunca comite chaves reais no código. 
    # Use 'openssl rand -hex 32' para gerar uma chave segura.
    SECRET_KEY: str = "change_this_to_a_secure_random_string_in_production"
    
    ADMIN_USER: str = "admin"
    # Sem valor padrão para senha forçar a configuração no .env em produção
    ADMIN_PASSWORD: str = "changeme" 

    # ==========================================
    # Banco de Dados
    # ==========================================
    DATABASE_URL: str = "sqlite+aiosqlite:///./portfolio.db"
    
    # ==========================================
    # Serviços Externos (GitHub & Gemini)
    # ==========================================
    GITHUB_TOKEN: Optional[str] = None
    GITHUB_USERNAME: str = "Dorminha"
    
    GEMINI_API_KEY: Optional[str] = None

    # ==========================================
    # Game Servers
    # ==========================================
    MINECRAFT_SERVER: str = "localhost"
    MINECRAFT_DISPLAY_NAME: Optional[str] = None
    
    ZOMBOID_SERVER: str = "localhost:16261"
    ZOMBOID_DISPLAY_NAME: Optional[str] = None

    # ==========================================
    # Discord Widget
    # ==========================================
    DISCORD_GUILD_ID: Optional[str] = None
    DISCORD_INVITE_URL: Optional[str] = None

    # ==========================================
    # Steam Integration
    # ==========================================
    STEAM_API_KEY: Optional[str] = None
    STEAM_ID: Optional[str] = None

    # Configuração Pydantic V2
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore", # Ignora variáveis extras no .env sem dar erro
        case_sensitive=True # Diferencia maiúsculas de minúsculas (padrão Linux)
    )

    def verify_password(self, plain_password: str) -> bool:
        """
        Verifica a senha de forma segura contra Timing Attacks.
        Utilizado pelo AuthService.
        """
        if not self.ADMIN_PASSWORD:
            return False
        return secrets.compare_digest(plain_password, self.ADMIN_PASSWORD)

@lru_cache()
def get_settings():
    """
    Retorna a instância de configurações em cache.
    Evita reler o arquivo .env a cada injeção de dependência.
    """
    return Settings()