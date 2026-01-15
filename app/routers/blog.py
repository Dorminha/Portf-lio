from math import ceil
from functools import lru_cache
from typing import Optional, List

from fastapi import APIRouter, Request, Depends, Query, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, func
from sqlalchemy.orm import defer
import markdown

from app.database import get_session
from app.models import Article

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# ==========================================
# SERVICE LAYER (Lógica de Negócio e Cache)
# ==========================================

class BlogService:
    PAGE_SIZE = 10
    
    # Cache: O Markdown só será reprocessado se o texto mudar.
    # maxsize=128 guarda os últimos 128 artigos acessados em memória RAM.
    @staticmethod
    @lru_cache(maxsize=128)
    def render_markdown(content: str) -> str:
        if not content:
            return ""
        return markdown.markdown(
            content, 
            extensions=['fenced_code', 'codehilite', 'tables', 'toc']
        )

    @staticmethod
    async def get_total_pages(session: AsyncSession) -> int:
        """Calcula o número total de páginas para a paginação."""
        statement = select(func.count()).select_from(Article).where(Article.is_published == True)
        result = await session.exec(statement)
        total_items = result.one()
        return ceil(total_items / BlogService.PAGE_SIZE)

# ==========================================
# ROTAS
# ==========================================

@router.get("/blog", response_class=HTMLResponse)
async def blog_list(
    request: Request, 
    page: int = Query(1, ge=1),
    session: AsyncSession = Depends(get_session)
):
    offset = (page - 1) * BlogService.PAGE_SIZE

    # 1. Busca os artigos (Otimizado com defer)
    statement = (
        select(Article)
        .where(Article.is_published == True)
        .options(defer(Article.content)) # Não traz o texto pesado
        .order_by(Article.published_at.desc())
        .offset(offset)
        .limit(BlogService.PAGE_SIZE)
    )
    result = await session.exec(statement)
    articles = result.all()
    
    # 2. Busca total de páginas (para saber se exibe botão "Próximo")
    # Nota: Em sites muito grandes, Count(*) pode ser lento. 
    # Alternativa: Buscar PAGE_SIZE + 1 itens.
    total_pages = await BlogService.get_total_pages(session)
    
    return templates.TemplateResponse("blog_list.html", {
        "request": request, 
        "articles": articles,
        "page": page,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    })

@router.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post(
    request: Request, 
    slug: str, 
    session: AsyncSession = Depends(get_session)
):
    # Busca segura
    statement = select(Article).where(Article.slug == slug, Article.is_published == True)
    result = await session.exec(statement)
    article = result.first()
    
    if not article:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=status.HTTP_404_NOT_FOUND)
        
    # Processamento com Cache
    # Se 100 pessoas acessarem esse post agora, o markdown só será gerado 1 vez.
    content_html = BlogService.render_markdown(article.content)
    
    return templates.TemplateResponse("blog_post.html", {
        "request": request, 
        "article": article, 
        "content": content_html,
        # Dados estruturados para SEO
        "meta_title": article.title,
        "meta_description": article.summary or article.title
    })