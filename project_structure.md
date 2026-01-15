# Estrutura do Projeto

```text
C:.
|   .env
|   consolidate_project.py    
|   database.db
|   download_audio.py
|   project_context.md        
|   requirements.txt
|
+---app
|   |   admin_routes_snippet.py
|   |   blog_routes_snippet.py
|   |   database.py
|   |   main.py
|   |   models.py
|   |   project_detail_snippet.py
|   |   sitemap_snippet.py    
|   |
|   +---core
|   |   |   config.py
|   |   |   i18n.py
|   |   |   security.py       
|   |
|   +---routers
|   |   |   admin.py
|   |   |   blog.py
|   |   |   chat.py
|   |   |   general.py        
|   |   |   projects.py       
|   |
|   +---services
|   |   |   github_service.py 
|   |   |   llm.py
|   |
|   +---static
|   |   +---audio
|   |   |       radiohead.mp3 
|   |   |
|   |   +---css
|   |   \---js
|   +---templates
|   |   |   about.html        
|   |   |   base.html
|   |   |   blog_list.html    
|   |   |   blog_post.html    
|   |   |   index.html        
|   |   |   project_detail.html
|   |   |
|   |   +---admin
|   |   |       dashboard.html
|   |   |       login.html    
|   |   |
|   |   \---partials
|   |           chat_messages.html
|   |           chat_widget.html
|   |           coding_stats.html
|   |           contact_success.html
|   |           project_list.html
|   |
|   \---__pycache__
|
\---tests
        run_tests.py
```

## Descrição dos Principais Diretórios e Arquivos

- **app/**: Contém o código fonte principal da aplicação.
  - **core/**: Configurações, segurança e internacionalização.
  - **routers/**: Definição das rotas da API e páginas (separadas por contexto).
  - **services/**: Lógica de negócios e integrações externas (GitHub, LLM).
  - **templates/**: Arquivos HTML (Jinja2) para o frontend.
  - **static/**: Arquivos estáticos (CSS, JS, Áudio).
  - **main.py**: Ponto de entrada da aplicação FastAPI.
  - **models.py**: Modelos de dados (SQLModel).
  - **database.py**: Configuração do banco de dados.

- **tests/**: Testes automatizados.
- **.env**: Variáveis de ambiente (Configurações sensíveis).
- **requirements.txt**: Dependências do projeto.
