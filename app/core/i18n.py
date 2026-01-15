from enum import Enum
from functools import lru_cache
from typing import Dict

class Language(str, Enum):
    """
    Define os idiomas suportados pela aplicação.
    Usar Enum evita erros de digitação como 'br' ou 'eng'.
    """
    PT = "pt"
    EN = "en"

# Dicionário protegido (começa com _) para evitar acesso direto fora deste arquivo
_TRANSLATIONS = {
    Language.PT: {
        # Navegação
        "nav_projects": "Projetos",
        "nav_about": "Sobre",
        "nav_blog": "Blog",
        "nav_contact": "Contato",
        
        # Hero Section
        "hero_title": "Full Stack Engineer & RPA Developer",
        "hero_subtitle": "Transformando café em código e ideias em realidade.",
        "btn_projects": "Ver Projetos",
        "btn_contact": "Entrar em Contato",
        
        # Footer & System
        "footer_rights": "© 2024 DEVFOLIO // SYSTEM.VER.3.2",
        "system_online": "Sistema Online",
        
        # Chat Widget
        "chat_placeholder": "Digite sua mensagem...",
        "chat_connect": "Conectando ao neural link...",
        
        # Gamification
        "achievement_title": "CONQUISTAS",
        "achievement_unlocked": "Conquista Desbloqueada",
        
        # UI Elements
        "theme_toggle": "Alternar Tema",
        "lang_toggle": "EN" # O botão mostra o idioma oposto
    },
    Language.EN: {
        "nav_projects": "Projects",
        "nav_about": "About",
        "nav_blog": "Blog",
        "nav_contact": "Contact",
        "hero_title": "Full Stack Engineer & RPA Developer",
        "hero_subtitle": "Turning coffee into code and ideas into reality.",
        "btn_projects": "View Projects",
        "btn_contact": "Get in Touch",
        "footer_rights": "© 2024 DEVFOLIO // SYSTEM.VER.3.2",
        "system_online": "System Online",
        "chat_placeholder": "Type your message...",
        "chat_connect": "Connecting to neural link...",
        "achievement_title": "ACHIEVEMENTS",
        "achievement_unlocked": "Achievement Unlocked",
        "theme_toggle": "Toggle Theme",
        "lang_toggle": "PT"
    }
}

@lru_cache()
def get_translations(lang: str) -> Dict[str, str]:
    """
    Retorna o dicionário de traduções para o idioma solicitado.
    Usa cache para performance e fallback seguro para PT.
    """
    # Tenta converter a string 'pt'/'en' para o Enum. 
    # Se falhar (usuário enviou 'fr'), cai no except e retorna PT.
    try:
        selected_lang = Language(lang)
    except ValueError:
        selected_lang = Language.PT

    return _TRANSLATIONS.get(selected_lang, _TRANSLATIONS[Language.PT])