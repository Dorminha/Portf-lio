
@app.get("/blog", response_class=HTMLResponse)
async def blog_list(request: Request, session: AsyncSession = Depends(get_session)):
    """
    Lista todos os artigos publicados.
    """
    statement = select(Article).where(Article.is_published == True).order_by(Article.published_at.desc())
    result = await session.exec(statement)
    articles = result.all()
    return templates.TemplateResponse("blog_list.html", {"request": request, "articles": articles})

@app.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post(request: Request, slug: str, session: AsyncSession = Depends(get_session)):
    """
    Exibe um artigo específico.
    """
    statement = select(Article).where(Article.slug == slug)
    result = await session.exec(statement)
    article = result.first()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
        
    content_html = markdown.markdown(article.content, extensions=['fenced_code', 'codehilite'])
    
    return templates.TemplateResponse("blog_post.html", {"request": request, "article": article, "content": content_html})
