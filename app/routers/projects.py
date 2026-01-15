import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request, Depends, HTTPException, Header, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
import markdown

from app.database import get_session
from app.models import Project
from app.services.github_service import GitHubService # Importando a classe otimizada

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# ==========================================
# SEGURANÇA
# ==========================================
# Em produção, isso deve vir de variáveis de ambiente (.env)
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "troque-isso-em-producao")

async def verify_admin_secret(x_admin_token: str = Header(None)):
    """
    Middleware simples para proteger a rota de sincronização.
    Pode ser chamado via Header ou Query param, aqui usamos Header.
    """
    if x_admin_token != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Acesso negado: Token inválido")

# ==========================================
# ROTAS DE PROJETOS
# ==========================================

@router.get("/projects/sync")
async def sync_projects(session: AsyncSession = Depends(get_session)):
    """
    Sincroniza projetos do GitHub com o Banco de Dados.
    Usa 'async with' para reutilizar a conexão HTTP (alta performance).
    """
    
    # Inicia o serviço usando o Context Manager (abre a conexão 1 vez)
    async with GitHubService() as gh_service:
        
        # 1. Busca lista de projetos no GitHub
        gh_projects = await gh_service.fetch_projects()
        
        if not gh_projects:
            return {"status": "skipped", "reason": "Nenhum projeto encontrado ou erro na API"}

        # 2. Mapeamento em Memória (Otimização de Banco)
        # Busca todos os projetos que já temos no banco para evitar fazer SELECT dentro do loop
        statement = select(Project)
        db_result = await session.exec(statement)
        existing_projects_map = {p.url: p for p in db_result.all()}
        
        count_new = 0
        count_updated = 0

        # 3. Processamento
        for gh_p in gh_projects:
            # Reutiliza a conexão aberta lá em cima para buscar o README
            readme_content = await gh_service.fetch_readme(gh_p.name)
            
            # Verifica se já existe pelo URL
            if gh_p.url in existing_projects_map:
                # ATUALIZA
                db_project = existing_projects_map[gh_p.url]
                db_project.stars = gh_p.stars
                db_project.description = gh_p.description
                db_project.updated_at = datetime.now(timezone.utc)
                
                # Atualiza o README se ele foi encontrado
                if readme_content:
                    db_project.readme_content = readme_content
                
                session.add(db_project)
                count_updated += 1
            else:
                # CRIA NOVO
                gh_p.readme_content = readme_content
                gh_p.created_at = datetime.now(timezone.utc)
                gh_p.updated_at = datetime.now(timezone.utc)
                
                session.add(gh_p)
                count_new += 1
        
        # Salva tudo de uma vez
        await session.commit()

    return {
        "status": "success", 
        "new": count_new, 
        "updated": count_updated,
        "total_synced": len(gh_projects)
    }

@router.get("/projects/more", response_class=HTMLResponse)
async def load_more_projects(
    request: Request, 
    page: int = 1, 
    session: AsyncSession = Depends(get_session)
):
    """
    Rota para paginação (Infinite Scroll ou botão 'Carregar Mais').
    """
    LIMIT = 6
    offset = page * LIMIT
    
    statement = select(Project).order_by(Project.stars.desc()).offset(offset).limit(LIMIT)
    result = await session.exec(statement)
    projects = result.all()
    
    # Se não houver mais projetos, retorna 204 (No Content) para o HTMX parar
    if not projects:
        return Response(status_code=204)
        
    return templates.TemplateResponse(
        "partials/project_list.html", 
        {"request": request, "projects": projects, "next_page": page + 1}
    )

@router.get("/projects/{name}", response_class=HTMLResponse)
async def project_detail(
    request: Request, 
    name: str, 
    session: AsyncSession = Depends(get_session)
):
    """
    Exibe os detalhes do projeto.
    NÃO faz requisição ao GitHub. Usa o cache do banco.
    """
    statement = select(Project).where(Project.name == name)
    result = await session.exec(statement)
    project = result.first()
    
    if not project:
        # Retorna uma página 404 bonita
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
        
    # Converte Markdown para HTML apenas na visualização
    content_html = ""
    if project.readme_content:
        content_html = markdown.markdown(
            project.readme_content, 
            extensions=['fenced_code', 'codehilite', 'tables']
        )
    
    return templates.TemplateResponse(
        "project_detail.html", 
        {
            "request": request, 
            "project": project, 
            "readme_content": content_html
        }
    )