
@app.get("/projects/{name}", response_class=HTMLResponse)
async def project_detail(
    request: Request, 
    name: str, 
    session: AsyncSession = Depends(get_session),
    gh_service: GitHubService = Depends(get_github_service)
):
    """
    Exibe detalhes do projeto e o README do GitHub.
    """
    statement = select(Project).where(Project.name == name)
    result = await session.exec(statement)
    project = result.first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    readme_md = await gh_service.fetch_readme(name)
    readme_html = markdown.markdown(readme_md, extensions=['fenced_code', 'codehilite']) if readme_md else None
    
    return templates.TemplateResponse(
        "project_detail.html", 
        {"request": request, "project": project, "readme_content": readme_html}
    )
