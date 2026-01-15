import secrets
from fastapi import APIRouter, Request, Depends, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.models import ContactMessage
from app.core.config import get_settings, Settings

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# ==========================================
# SERVIÇOS AUXILIARES (Lógica de Negócio)
# ==========================================

class AuthService:
    """
    Responsável por validar credenciais e gerenciar regras de autenticação.
    """
    @staticmethod
    def verify_admin_credentials(
        username: str, 
        password: str, 
        settings: Settings
    ) -> bool:
        """
        Verifica credenciais de forma segura contra Timing Attacks.
        """
        # secrets.compare_digest leva o mesmo tempo para validar, 
        # independente de onde o erro ocorre na string.
        is_user_ok = secrets.compare_digest(username, settings.ADMIN_USER)
        is_pass_ok = secrets.compare_digest(password, settings.ADMIN_PASSWORD)
        return is_user_ok and is_pass_ok

# Dependência para proteger rotas
def require_admin_login(request: Request):
    """
    Dependência que verifica se o usuário está logado.
    Se não estiver, redireciona para o login.
    """
    user = request.session.get("user")
    if not user:
        # Nota: Em APIs REST retornamos 401, mas em Apps Web redirecionamos.
        # A maneira mais limpa em FastAPI sem middleware complexo é fazer o check na rota
        # ou lançar uma exceção que um ExceptionHandler trata. 
        # Para manter simples e funcional aqui, retornamos None e tratamos na rota.
        return None
    return user

# ==========================================
# ROTAS
# ==========================================

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """
    Exibe página de login. 
    Melhoria: Se já estiver logado, manda direto pro admin.
    """
    if request.session.get("user"):
        return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
        
    return templates.TemplateResponse("admin/login.html", {"request": request})

@router.post("/login", response_class=HTMLResponse)
async def login(
    request: Request, 
    username: str = Form(...), 
    password: str = Form(...),
    settings: Settings = Depends(get_settings)
):
    """
    Processa o login de forma segura.
    """
    if AuthService.verify_admin_credentials(username, password, settings):
        request.session["user"] = username
        return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
        
    return templates.TemplateResponse(
        "admin/login.html", 
        {
            "request": request, 
            "error": "Credenciais inválidas. Verifique usuário e senha."
        }
    )

@router.get("/logout")
async def logout(request: Request):
    """
    Limpa a sessão e redireciona.
    """
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request, 
    session: AsyncSession = Depends(get_session)
):
    """
    Dashboard administrativo.
    """
    # Verificação de segurança explícita (Guard Clause)
    if not require_admin_login(request):
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    
    # Busca de dados
    statement = select(ContactMessage).order_by(ContactMessage.sent_at.desc())
    result = await session.exec(statement)
    messages = result.all()
    
    return templates.TemplateResponse(
        "admin/dashboard.html", 
        {"request": request, "messages": messages}
    )