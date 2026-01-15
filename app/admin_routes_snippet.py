
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """
    Página de login do admin.
    """
    return templates.TemplateResponse("admin/login.html", {"request": request})

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """
    Processa o login.
    """
    # TODO: Usar variáveis de ambiente para credenciais
    if username == "admin" and password == "admin123": 
        request.session["user"] = username
        return RedirectResponse(url="/admin", status_code=303)
    return templates.TemplateResponse("admin/login.html", {"request": request, "error": "Credenciais inválidas"})

@app.get("/logout")
async def logout(request: Request):
    """
    Faz logout e limpa a sessão.
    """
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, session: AsyncSession = Depends(get_session)):
    """
    Dashboard administrativo protegido.
    """
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=303)
    
    # Busca mensagens de contato
    statement = select(ContactMessage).order_by(ContactMessage.sent_at.desc())
    result = await session.exec(statement)
    messages = result.all()
    
    return templates.TemplateResponse("admin/dashboard.html", {"request": request, "messages": messages})
