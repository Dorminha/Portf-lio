import time
import re
from datetime import datetime
from typing import Optional
import asyncio

from fastapi import APIRouter, Request, Depends, Form, status
from fastapi.responses import HTMLResponse, Response, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, text, func

from app.database import get_session
from app.models import Project, ContactMessage
from app.core.config import get_settings
from app.services.game_status import get_minecraft_status, get_zomboid_status, get_discord_status
from app.services.steam_service import get_steam_profile

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Validação simples de email via Regex
EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")

@router.get("/", response_class=HTMLResponse)
async def read_root(request: Request, session: AsyncSession = Depends(get_session)):
    # Otimização: Traz apenas colunas necessárias se o model for pesado
    statement = select(Project).order_by(Project.stars.desc()).limit(6)
    result = await session.exec(statement)
    projects = result.all()
    
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "projects": projects}
    )

@router.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    settings = get_settings()
    return templates.TemplateResponse("about.html", {
        "request": request,
        "github_username": settings.GITHUB_USERNAME,
        # Lógica movida para o template (ou calculada aqui de forma limpa)
        "github_avatar": f"https://github.com/{settings.GITHUB_USERNAME}.png"
    })

@router.post("/contact", response_class=HTMLResponse)
async def submit_contact(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    message: str = Form(...),
    # Campo isca (Honeypot): Deve estar oculto no HTML (style="display:none")
    # Se um bot preencher, sabemos que é spam.
    confirm_email: Optional[str] = Form(None), 
    session: AsyncSession = Depends(get_session)
):
    # 1. Anti-Spam (Honeypot)
    if confirm_email:
        # Finge que deu certo para enganar o bot, mas não salva nada
        return templates.TemplateResponse("partials/contact_success.html", {"request": request, "name": name})

    # 2. Validações Básicas
    if not EMAIL_REGEX.match(email):
        return Response("E-mail inválido", status_code=400)
    
    if len(message) > 2000:
        return Response("Mensagem muito longa", status_code=400)

    # 3. Salva no Banco
    contact = ContactMessage(name=name, email=email, message=message)
    session.add(contact)
    await session.commit()

    return templates.TemplateResponse(
        "partials/contact_success.html", 
        {"request": request, "name": name}
    )

@router.get("/set-language/{lang}")
async def set_language(lang: str, request: Request):
    if lang not in ["pt", "en"]:
        lang = "pt"
    
    # Segurança: Fallback para '/' se não houver referer
    redirect_url = request.headers.get("referer") or "/"
    
    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    # Cookie Seguro: HttpOnly impede JS de ler, SameSite previne CSRF
    response.set_cookie(key="lang", value=lang, max_age=31536000, httponly=True, samesite="Lax")
    
    return response

@router.get("/api/status")
async def get_status(session: AsyncSession = Depends(get_session)):
    start_time = time.time()
    
    try:
        # Executa query leve
        await session.exec(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    latency = (time.time() - start_time) * 1000
    
    return {
        "status": "online",
        "latency_ms": round(latency, 2),
        "database": db_status,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

@router.get("/api/servers", response_class=HTMLResponse)
async def get_servers(request: Request):
    settings = get_settings()
    # Parse Zomboid IP/Port
    zomboid_host = settings.ZOMBOID_SERVER
    print(f"Querying Servers: MC={settings.MINECRAFT_SERVER}, PZ={zomboid_host}, Discord={settings.DISCORD_GUILD_ID}") # Debug log
    
    z_ip, z_port = zomboid_host.split(":") if ":" in zomboid_host else (zomboid_host, 16261)
    
    # Fetch statuses in parallel
    mc_task = get_minecraft_status(settings.MINECRAFT_SERVER)
    pz_task = get_zomboid_status(z_ip, int(z_port))
    discord_task = get_discord_status(settings.DISCORD_GUILD_ID)
    
    mc_status, pz_status, discord_status = await asyncio.gather(mc_task, pz_task, discord_task)
    
    # Apply Custom Display Names
    if settings.MINECRAFT_DISPLAY_NAME:
        mc_status["motd"] = settings.MINECRAFT_DISPLAY_NAME
        
    if settings.ZOMBOID_DISPLAY_NAME:
        pz_status["server_name"] = settings.ZOMBOID_DISPLAY_NAME
    
    return templates.TemplateResponse(
        "partials/server_grid.html",
        {
            "request": request,
            "minecraft": mc_status,
            "zomboid": pz_status,
            "discord": discord_status
        }
    )

@router.get("/api/steam", response_class=HTMLResponse)
async def get_steam(request: Request):
    steam_data = await get_steam_profile()
    return templates.TemplateResponse(
        "partials/steam_grid.html",
        {"request": request, "steam": steam_data}
    )

@router.get("/sitemap.xml", response_class=Response)
async def sitemap(request: Request, session: AsyncSession = Depends(get_session)):
    # 1. Busca a data do projeto mais recente para atualizar o lastmod
    statement = select(func.max(Project.updated_at))
    result = await session.exec(statement)
    latest_update = result.first() or datetime.now()
    
    # Formata data para W3C format (YYYY-MM-DD)
    date_str = latest_update.strftime("%Y-%m-%d") if isinstance(latest_update, datetime) else latest_update
    
    # 2. Usa a URL base dinamicamente (funciona em localhost e prod sem mudar código)
    base_url = str(request.base_url).rstrip("/")

    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>{base_url}/</loc>
        <lastmod>{date_str}</lastmod>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>
    <url>
        <loc>{base_url}/#projects</loc>
        <lastmod>{date_str}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.8</priority>
    </url>
    <url>
        <loc>{base_url}/about</loc>
        <changefreq>monthly</changefreq>
        <priority>0.5</priority>
    </url>
</urlset>"""
    return Response(content=content, media_type="application/xml")