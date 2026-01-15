# Project Context: DevFolio Dinâmico

## File: app\main.py
```python
from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from contextlib import asynccontextmanager

from app.database import init_db, get_session
from app.models import Project, ContactMessage
from app.services.github_service import GitHubService

# Configuração do ciclo de vida da aplicação
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Executa na inicialização e desligamento da app.
    Inicializa o banco de dados.
    """
    await init_db()
    yield

app = FastAPI(lifespan=lifespan)

# Monta arquivos estáticos (CSS, JS)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Configura templates Jinja2
templates = Jinja2Templates(directory="app/templates")

# Instância do serviço GitHub (idealmente injetado)
github_service = GitHubService(username="seu-usuario-github") # TODO: Configurar usuário

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, session: AsyncSession = Depends(get_session)):
    """
    Rota principal. Renderiza a página inicial com os projetos.
    """
    # Busca projetos do banco de dados
    statement = select(Project).order_by(Project.stars.desc()).limit(6)
    result = await session.exec(statement)
    projects = result.all()
    
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "projects": projects}
    )


@app.get("/projects/sync")
async def sync_projects(session: AsyncSession = Depends(get_session)):
    """
    Sincroniza projetos do GitHub e salva no banco.
    Pode ser chamado via botão ou cron job.
    """
    new_projects = await github_service.fetch_projects()
    
    # Limpa projetos antigos e insere novos (estratégia simples de cache)
    # Em produção, faríamos um 'upsert' ou verificação mais inteligente
    if new_projects:
        # Deleta todos os projetos existentes
        statement = select(Project)
        results = await session.exec(statement)
        for project in results.all():
            await session.delete(project)
        
        # Adiciona os novos
        for project in new_projects:
            session.add(project)
        
        await session.commit()
        
    return {"status": "success", "count": len(new_projects)}

@app.get("/projects/more", response_class=HTMLResponse)
async def load_more_projects(request: Request, page: int = 1, session: AsyncSession = Depends(get_session)):
    """
    Rota para Infinite Scroll via HTMX.
    Retorna apenas o HTML dos próximos projetos.
    """
    limit = 6
    offset = page * limit
    statement = select(Project).order_by(Project.stars.desc()).offset(offset).limit(limit)
    result = await session.exec(statement)
    projects = result.all()
    
    if not projects:
        return "" # Retorna vazio se não houver mais projetos
        
    return templates.TemplateResponse(
        "partials/project_list.html", 
        {"request": request, "projects": projects, "next_page": page + 1}
    )

@app.post("/contact", response_class=HTMLResponse)
async def submit_contact(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    message: str = Form(...),
    session: AsyncSession = Depends(get_session)
):
    """
    Processa o formulário de contato via HTMX.
    Salva no banco e retorna mensagem de sucesso.
    """
    contact = ContactMessage(name=name, email=email, message=message)
    session.add(contact)
    await session.commit()
    
@app.get("/api/status")
async def get_status(session: AsyncSession = Depends(get_session)):
    """
    Endpoint para monitoramento de status do sistema (Health Check).
    Simula uma verificação de infraestrutura.
    """
    import time
    start_time = time.time()
    
    try:
        # Verifica conexão com DB
        await session.exec(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    latency = (time.time() - start_time) * 1000
    
    return {
        "status": "online",
        "latency_ms": round(latency, 2),
        "database": db_status,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

```

## File: app\models.py
```python
from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel

class Project(SQLModel, table=True):
    """
    Modelo de dados para os projetos do portfólio.
    Armazena informações sincronizadas do GitHub.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    url: str
    stars: int = Field(default=0)
    language: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ContactMessage(SQLModel, table=True):
    """
    Modelo para mensagens de contato enviadas pelo formulário.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str
    message: str
    sent_at: datetime = Field(default_factory=datetime.utcnow)

```

## File: app\database.py
```python
from sqlmodel import SQLModel, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
import os

# URL de conexão com o banco de dados.
# Em produção, isso deve vir de variáveis de ambiente.
# Exemplo para PostgreSQL: postgresql+asyncpg://user:password@localhost/dbname
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./database.db")

# Cria o engine assíncrono
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

async def init_db():
    """
    Inicializa o banco de dados, criando as tabelas se não existirem.
    """
    async with engine.begin() as conn:
        # await conn.run_sync(SQLModel.metadata.drop_all) # Descomente para resetar o DB
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session() -> AsyncSession:
    """
    Dependência para obter uma sessão assíncrona do banco de dados.
    """
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

```

## File: app\services\github_service.py
```python
import httpx
from typing import List, Optional
from app.models import Project

class GitHubService:
    """
    Serviço responsável por interagir com a API do GitHub.
    Usa httpx para requisições assíncronas.
    """
    BASE_URL = "https://api.github.com"

    def __init__(self, username: str = "seu-usuario-github"):
        # TODO: Tornar o usuário configurável via variável de ambiente
        self.username = username

    async def fetch_projects(self) -> List[Project]:
        """
        Busca os repositórios públicos do usuário no GitHub.
        Filtra e converte para o modelo Project.
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/users/{self.username}/repos?sort=updated&per_page=100",
                    headers={"Accept": "application/vnd.github.v3+json"}
                )
                response.raise_for_status()
                repos = response.json()

                projects = []
                for repo in repos:
                    # Filtra apenas projetos com descrição e linguagem (opcional, regra de negócio)
                    if repo.get("description"): 
                        project = Project(
                            name=repo["name"],
                            description=repo["description"],
                            url=repo["html_url"],
                            stars=repo["stargazers_count"],
                            language=repo["language"]
                        )
                        projects.append(project)
                
                # Ordena por estrelas (decrescente) como critério de "melhores projetos"
                projects.sort(key=lambda x: x.stars, reverse=True)
                return projects

            except httpx.HTTPStatusError as e:
                print(f"Erro ao buscar projetos do GitHub: {e}")
                return []
            except Exception as e:
                print(f"Erro inesperado: {e}")
                return []

```

## File: app\templates\base.html
```html
<!DOCTYPE html>
<html lang="pt-br">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DevFolio Dinâmico</title>
    <!-- TailwindCSS via CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- HTMX via CDN -->
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <!-- Configuração do Tailwind para tema Purple/Retro Professional -->
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        'retro-bg': '#0f0e17',
                        'retro-card': '#23212d',
                        'retro-text': '#fffffe',
                        'retro-muted': '#a7a9be',
                        'retro-accent': '#ff8906',
                        'retro-secondary': '#f25f4c',
                        'retro-purple': '#e53170',
                    },
                    fontFamily: {
                        sans: ['Inter', 'sans-serif'],
                        mono: ['Fira Code', 'monospace'],
                    }
                }
            }
        }
    </script>
    <link
        href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Fira+Code:wght@400;600&display=swap"
        rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', sans-serif;
        }

        h1,
        h2,
        h3,
        .font-mono {
            font-family: 'Fira Code', monospace;
        }

        /* Noise Texture for "Soul" */
        .bg-noise {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 50;
            opacity: 0.03;
            background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E");
        }

        /* HTMX Indicator */
        .htmx-indicator {
            opacity: 0;
            transition: opacity 200ms ease-in;
        }

        .htmx-request .htmx-indicator {
            opacity: 1;
        }

        .htmx-request.htmx-indicator {
            opacity: 1;
        }

        /* Elegant Equalizer (Thinner, slower) */
        @keyframes equalize {
            0% {
                height: 20%;
            }

            50% {
                height: 100%;
            }

            100% {
                height: 20%;
            }
        }

        .equalizer-bar {
            animation: equalize 1.5s infinite ease-in-out;
            width: 2px;
            background: #ff8906;
            border-radius: 1px;
        }

        .equalizer-bar:nth-child(odd) {
            background: #e53170;
        }

        .equalizer-bar:nth-child(1) {
            animation-delay: 0.0s;
        }

        .equalizer-bar:nth-child(2) {
            animation-delay: 0.2s;
        }

        .equalizer-bar:nth-child(3) {
            animation-delay: 0.4s;
        }

        .equalizer-bar:nth-child(4) {
            animation-delay: 0.1s;
        }

        .equalizer-bar:nth-child(5) {
            animation-delay: 0.3s;
        }

        /* Smooth Fade In */
        .fade-in-up {
            animation: fadeInUp 0.8s ease-out forwards;
            opacity: 0;
            transform: translateY(20px);
        }

        @keyframes fadeInUp {
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
    </style>
</head>

<body
    class="bg-retro-bg text-retro-text min-h-screen flex flex-col selection:bg-retro-purple selection:text-white relative">
    <div class="bg-noise"></div>

    <!-- Navbar -->
    <nav class="bg-retro-bg/90 backdrop-blur-md sticky top-0 z-50 border-b border-white/10">
        <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between h-16 items-center">
                <div class="flex-shrink-0 flex items-center gap-2">
                    <div class="w-3 h-3 rounded-full bg-retro-accent"></div>
                    <span class="font-bold text-xl tracking-tight text-white">Dev<span
                            class="text-retro-purple">Folio</span></span>
                </div>
                <div class="hidden md:flex space-x-8">
                    <a href="#projects"
                        class="text-retro-muted hover:text-retro-accent transition-colors font-medium text-sm">PROJETOS</a>
                    <a href="#about"
                        class="text-retro-muted hover:text-retro-accent transition-colors font-medium text-sm">SOBRE</a>
                    <a href="#contact"
                        class="text-retro-muted hover:text-retro-accent transition-colors font-medium text-sm">CONTATO</a>
                </div>
            </div>
        </div>
    </nav>

    <!-- Conteúdo Principal -->
    <main class="flex-grow">
        {% block content %}{% endblock %}
    </main>

    <!-- Footer -->
    <footer class="bg-retro-card mt-20 py-10 border-t border-white/5">
        <div class="max-w-6xl mx-auto px-4 flex flex-col md:flex-row justify-between items-center gap-6">
            <div class="text-retro-muted text-sm">
                <p>&copy; 2024 DevFolio. <span class="text-retro-purple">Python</span> + <span
                        class="text-retro-accent">HTMX</span>.</p>
            </div>

            <!-- System Status Monitor -->
            <div class="flex items-center gap-4 bg-retro-bg px-4 py-2 rounded-lg border border-white/5 font-mono text-xs"
                hx-get="/api/status" hx-trigger="load, every 30s">
                <div class="flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                    <span class="text-retro-muted">System:</span>
                    <span class="text-green-400">Online</span>
                </div>
                <div class="w-px h-4 bg-white/10"></div>
                <div class="flex items-center gap-2">
                    <span class="text-retro-muted">Latency:</span>
                    <span class="text-white">...ms</span>
                </div>
            </div>
        </div>
    </footer>

    <!-- Interactive CLI Overlay -->
    <div id="cli-overlay"
        class="fixed inset-0 bg-black/80 backdrop-blur-sm z-[60] hidden flex items-center justify-center p-4">
        <div
            class="bg-retro-bg w-full max-w-2xl rounded-lg border border-white/10 shadow-2xl overflow-hidden font-mono text-sm">
            <!-- Terminal Header -->
            <div class="bg-retro-card px-4 py-2 flex justify-between items-center border-b border-white/5">
                <div class="flex gap-2">
                    <div class="w-3 h-3 rounded-full bg-red-500 cursor-pointer" onclick="toggleCLI()"></div>
                    <div class="w-3 h-3 rounded-full bg-yellow-500"></div>
                    <div class="w-3 h-3 rounded-full bg-green-500"></div>
                </div>
                <span class="text-retro-muted">visitor@devfolio:~$</span>
            </div>

            <!-- Terminal Body -->
            <div class="p-6 h-80 overflow-y-auto" id="cli-output"
                onclick="document.getElementById('cli-input').focus()">
                <div class="mb-2 text-retro-muted">Welcome to DevFolio CLI v1.0.0</div>
                <div class="mb-4 text-white">Type <span class="text-retro-accent">'help'</span> to
                    see available
                    commands.</div>

                <!-- Output Area -->
                <div id="cli-history"></div>

                <!-- Input Line -->
                <div class="flex gap-2 text-white">
                    <span class="text-retro-purple">➜</span>
                    <span class="text-retro-accent">~</span>
                    <input type="text" id="cli-input"
                        class="bg-transparent border-none outline-none flex-grow text-white" autocomplete="off">
                </div>
            </div>
        </div>
    </div>

    <!-- Libraries -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/vanilla-tilt/1.8.1/vanilla-tilt.min.js"></script>
    <script src="https://unpkg.com/scrollreveal"></script>

    <script>
        // --- 1. Network Graph (Particles) ---
        const canvas = document.createElement('canvas');
        canvas.id = 'network-bg';
        canvas.style.position = 'fixed';
        canvas.style.top = '0';
        canvas.style.left = '0';
        canvas.style.width = '100%';
        canvas.style.height = '100%';
        canvas.style.pointerEvents = 'none';
        canvas.style.zIndex = '-1';
        document.body.appendChild(canvas);

        const ctx = canvas.getContext('2d');
        let width, height;
        let particles = [];

        function resize() {
            width = canvas.width = window.innerWidth;
            height = canvas.height = window.innerHeight;
        }
        window.addEventListener('resize', resize);
        resize();

        class Particle {
            constructor() {
                this.x = Math.random() * width;
                this.y = Math.random() * height;
                this.vx = (Math.random() - 0.5) * 0.5;
                this.vy = (Math.random() - 0.5) * 0.5;
                this.size = Math.random() * 2 + 1;
            }
            update() {
                this.x += this.vx;
                this.y += this.vy;
                if (this.x < 0 || this.x > width) this.vx *= -1;
                if (this.y < 0 || this.y > height) this.vy *= -1;
            }
            draw() {
                ctx.fillStyle = 'rgba(229, 49, 112, 0.5)'; // Retro Purple
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        function initParticles() {
            particles = [];
            for (let i = 0; i < 50; i++) particles.push(new Particle());
        }
        initParticles();

        function animateParticles() {
            ctx.clearRect(0, 0, width, height);
            for (let i = 0; i < particles.length; i++) {
                particles[i].update();
                particles[i].draw();
                for (let j = i; j < particles.length; j++) {
                    const dx = particles[i].x - particles[j].x;
                    const dy = particles[i].y - particles[j].y;
                    const distance = Math.sqrt(dx * dx + dy * dy);
                    if (distance < 150) {
                        ctx.strokeStyle = `rgba(255, 137, 6, ${1 - distance / 150})`; // Retro Accent
                        ctx.lineWidth = 0.5;
                        ctx.beginPath();
                        ctx.moveTo(particles[i].x, particles[i].y);
                        ctx.lineTo(particles[j].x, particles[j].y);
                        ctx.stroke();
                    }
                }
            }
            requestAnimationFrame(animateParticles);
        }
        animateParticles();

        // --- 2. Magnetic Buttons ---
        document.querySelectorAll('button, a.group').forEach(btn => {
            btn.addEventListener('mousemove', (e) => {
                const rect = btn.getBoundingClientRect();
                const x = e.clientX - rect.left - rect.width / 2;
                const y = e.clientY - rect.top - rect.height / 2;
                btn.style.transform = `translate(${x * 0.2}px, ${y * 0.2}px)`;
            });
            btn.addEventListener('mouseleave', () => {
                btn.style.transform = 'translate(0, 0)';
            });
        });

        // --- 3. Scroll Reveal ---
        ScrollReveal().reveal('.reveal', {
            delay: 200,
            distance: '20px',
            origin: 'bottom',
            opacity: 0,
            duration: 800,
            easing: 'cubic-bezier(0.5, 0, 0, 1)'
        });

        // --- CLI Logic ---
        function toggleCLI() {
            const cli = document.getElementById('cli-overlay');
            cli.classList.toggle('hidden');
            if (!cli.classList.contains('hidden')) {
                document.getElementById('cli-input').focus();
            }
        }

        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'k') {
                e.preventDefault();
                toggleCLI();
            }
            if (e.key === 'Escape') {
                document.getElementById('cli-overlay').classList.add('hidden');
            }
        });

        const commands = {
            help: "Available commands: <br> - <span class='text-retro-accent'>about</span>: Show bio <br> - <span class='text-retro-accent'>projects</span>: List projects <br> - <span class='text-retro-accent'>contact</span>: Show contact info <br> - <span class='text-retro-accent'>clear</span>: Clear terminal",
            about: "Luan de Paz. Full Stack Engineer with Infrastructure background. Python, FastAPI, React.",
            projects: "Check out the 'Projects' section for my latest work.",
            contact: "Email: contact@luandepaz.dev (Example)",
            clear: "CLEAR",
            sudo: "Permission denied: You are not root."
        };

        document.getElementById('cli-input').addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                const input = this.value.trim().toLowerCase();
                const history = document.getElementById('cli-history');
                history.innerHTML += `<div class="mb-1"><span class="text-retro-purple">➜</span> <span class="text-retro-accent">~</span> ${this.value}</div>`;
                if (commands[input]) {
                    if (commands[input] === "CLEAR") {
                        history.innerHTML = "";
                    } else {
                        history.innerHTML += `<div class="mb-4 text-retro-muted">${commands[input]}</div>`;
                    }
                } else if (input !== "") {
                    history.innerHTML += `<div class="mb-4 text-red-400">Command not found: ${input}</div>`;
                }
                this.value = "";
                const output = document.getElementById('cli-output');
                output.scrollTop = output.scrollHeight;
            }
        });
    </script>
</body>

</html>
```

## File: app\templates\index.html
```html
{% extends "base.html" %}

{% block content %}
<!-- Hero Section: Professional Tech Atmosphere -->
<section class="relative py-32 lg:py-48 overflow-hidden">
    <!-- Subtle Background Glow -->
    <div class="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full z-0 pointer-events-none">
        <div class="absolute top-20 left-1/4 w-[500px] h-[500px] bg-retro-purple/10 rounded-full blur-[100px]"></div>
        <div class="absolute bottom-0 right-1/4 w-[400px] h-[400px] bg-retro-accent/10 rounded-full blur-[80px]"></div>
    </div>

    <div class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-center">
        <!-- Intro Tag -->
        <div class="inline-flex items-center gap-3 mb-8 fade-in-up" style="animation-delay: 0.1s;">
            <div class="flex gap-1 h-4 items-end">
                <div class="equalizer-bar h-2"></div>
                <div class="equalizer-bar h-4"></div>
                <p class="text-retro-muted font-mono text-sm">Histórico de Commits Profissionais</p>
            </div>

            <div class="relative border-l-2 border-white/10 ml-4 md:ml-0 space-y-12">
                <!-- Commit 1: Current -->
                <div class="relative pl-8 md:pl-12 group">
                    <div
                        class="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-retro-purple border-4 border-retro-bg group-hover:scale-125 transition-transform">
                    </div>
                    <div class="flex flex-col md:flex-row gap-4 md:items-baseline">
                        <span class="font-mono text-retro-accent text-sm">HEAD -> main</span>
                        <h3 class="text-xl font-bold text-white">Full Stack & RPA Developer</h3>
                        <span class="text-retro-muted text-sm font-mono">2024 - Presente</span>
                    </div>
                    <p class="text-retro-muted mt-2 leading-relaxed">
                        Desenvolvimento de soluções completas com FastAPI e React. Orquestração de automações RPA para
                        otimização de processos de negócio.
                    </p>
                    <div class="mt-3 flex gap-2">
                        <span class="px-2 py-1 bg-retro-purple/10 text-retro-purple text-xs font-mono rounded">feat:
                            dev-folio</span>
                        <span class="px-2 py-1 bg-retro-purple/10 text-retro-purple text-xs font-mono rounded">feat:
                            api-integrations</span>
                    </div>
                </div>

                <!-- Commit 2: Transition -->
                <div class="relative pl-8 md:pl-12 group">
                    <div
                        class="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-retro-accent border-4 border-retro-bg group-hover:scale-125 transition-transform">
                    </div>
                    <div class="flex flex-col md:flex-row gap-4 md:items-baseline">
                        <span class="font-mono text-retro-muted text-sm">a1b2c3d</span>
                        <h3 class="text-xl font-bold text-white">Transição para Desenvolvimento</h3>
                        <span class="text-retro-muted text-sm font-mono">2022 - 2023</span>
                    </div>
                    <p class="text-retro-muted mt-2 leading-relaxed">
                        Migração do foco de Infraestrutura pura para Engenharia de Software. Uso intensivo de Python
                        para
                        criar ferramentas de automação de servidores e scripts de manutenção.
                    </p>
                    <div class="mt-3 flex gap-2">
                        <span class="px-2 py-1 bg-retro-accent/10 text-retro-accent text-xs font-mono rounded">refactor:
                            career-path</span>
                        <span class="px-2 py-1 bg-retro-accent/10 text-retro-accent text-xs font-mono rounded">chore:
                            learn-python</span>
                    </div>
                </div>

                <!-- Commit 3: Infra -->
                <div class="relative pl-8 md:pl-12 group">
                    <div
                        class="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-white/20 border-4 border-retro-bg group-hover:scale-125 transition-transform">
                    </div>
                    <div class="flex flex-col md:flex-row gap-4 md:items-baseline">
                        <span class="font-mono text-retro-muted text-sm">9f8e7d6</span>
                        <h3 class="text-xl font-bold text-white">Analista de Infraestrutura</h3>
                        <span class="text-retro-muted text-sm font-mono">2018 - 2022</span>
                    </div>
                    <p class="text-retro-muted mt-2 leading-relaxed">
                        Gerenciamento de servidores Linux/Windows, redes e virtualização. Garantia de uptime e
                        segurança. A
                        base sólida que hoje sustenta meu código.
                    </p>
                    <div class="mt-3 flex gap-2">
                        <span class="px-2 py-1 bg-white/5 text-retro-muted text-xs font-mono rounded">ops:
                            server-maintenance</span>
                        <span class="px-2 py-1 bg-white/5 text-retro-muted text-xs font-mono rounded">fix:
                            network-issues</span>
                    </div>
                </div>

                <!-- Commit 4: Support -->
                <div class="relative pl-8 md:pl-12 group">
                    <div
                        class="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-white/20 border-4 border-retro-bg group-hover:scale-125 transition-transform">
                    </div>
                    <div class="flex flex-col md:flex-row gap-4 md:items-baseline">
                        <span class="font-mono text-retro-muted text-sm">init</span>
                        <h3 class="text-xl font-bold text-white">Suporte Técnico</h3>
                        <span class="text-retro-muted text-sm font-mono">2016 - 2018</span>
                    </div>
                    <p class="text-retro-muted mt-2 leading-relaxed">
                        O início de tudo. Resolução de problemas de hardware e software, atendimento ao usuário. Onde
                        aprendi a investigar a causa raiz.
                    </p>
                </div>
            </div>
        </div>
</section>

<!-- Projects Section -->
<section id="projects" class="py-24 border-t border-white/5">
    <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex flex-col md:flex-row justify-between items-end mb-16 gap-6">
            <div>
                <h2 class="text-4xl font-bold text-white mb-2">Projetos</h2>
                <p class="text-retro-muted">Arquitetura e Código.</p>
            </div>
            <button hx-get="/projects/sync" hx-swap="none"
                class="text-retro-accent hover:text-white transition-colors text-sm font-mono flex items-center gap-2">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15">
                    </path>
                </svg>
                Sync GitHub Repos
            </button>
        </div>

        <div id="projects-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {% include "partials/project_list.html" %}
        </div>
    </div>
</section>

<!-- Contact Section -->
<section id="contact" class="py-24 border-t border-white/5 bg-retro-bg">
    <div class="max-w-3xl mx-auto px-4 text-center">
        <h2 class="text-3xl font-bold text-white mb-6">Contato Profissional</h2>
        <p class="text-retro-muted mb-12">
            Disponível para projetos de automação, desenvolvimento backend e consultoria de infraestrutura.
        </p>

        <form hx-post="/contact" hx-swap="outerHTML" class="text-left space-y-8">
            <div class="group relative">
                <input type="text" name="name" id="name" required placeholder=" "
                    class="peer w-full bg-transparent border-b border-white/20 py-3 text-white focus:border-retro-accent focus:outline-none transition-colors">
                <label for="name"
                    class="absolute left-0 top-3 text-retro-muted transition-all peer-focus:-top-4 peer-focus:text-xs peer-focus:text-retro-accent peer-not-placeholder-shown:-top-4 peer-not-placeholder-shown:text-xs">
                    NOME
                </label>
            </div>

            <div class="group relative">
                <input type="email" name="email" id="email" required placeholder=" "
                    class="peer w-full bg-transparent border-b border-white/20 py-3 text-white focus:border-retro-accent focus:outline-none transition-colors">
                <label for="email"
                    class="absolute left-0 top-3 text-retro-muted transition-all peer-focus:-top-4 peer-focus:text-xs peer-focus:text-retro-accent peer-not-placeholder-shown:-top-4 peer-not-placeholder-shown:text-xs">
                    EMAIL
                </label>
            </div>

            <div class="group relative">
                <textarea name="message" id="message" rows="3" required placeholder=" "
                    class="peer w-full bg-transparent border-b border-white/20 py-3 text-white focus:border-retro-accent focus:outline-none transition-colors resize-none"></textarea>
                <label for="message"
                    class="absolute left-0 top-3 text-retro-muted transition-all peer-focus:-top-4 peer-focus:text-xs peer-focus:text-retro-accent peer-not-placeholder-shown:-top-4 peer-not-placeholder-shown:text-xs">
                    MENSAGEM
                </label>
            </div>

            <div class="pt-6 text-center">
                <button type="submit"
                    class="bg-white text-retro-bg px-12 py-4 rounded-full font-bold hover:bg-retro-accent hover:text-white transition-all shadow-lg flex items-center justify-center gap-2 mx-auto disabled:opacity-50">
                    ENVIAR MENSAGEM
                    <img class="htmx-indicator h-5 w-5"
                        src="https://raw.githubusercontent.com/n3r4zzurr0/svg-spinners/main/svg-css/90-ring-with-bg.svg"
                        alt="...">
                </button>
            </div>
        </form>
    </div>
</section>
{% endblock %}
```

## File: app\templates\partials\project_list.html
```html
{% for project in projects %}
<div class="bg-retro-card rounded-xl p-6 border border-white/5 hover:border-retro-purple/50 transition-all hover:-translate-y-1 flex flex-col h-full group relative reveal"
    data-tilt data-tilt-max="5" data-tilt-speed="400" data-tilt-glare data-tilt-max-glare="0.2">
    <div class="flex justify-between items-start mb-4">
        <h3 class="text-lg font-bold text-white group-hover:text-retro-purple transition-colors">{{ project.name }}</h3>
        <span class="bg-retro-bg border border-white/10 text-retro-accent text-xs font-mono px-2 py-1 rounded">
            {{ project.stars }} ★
        </span>
    </div>
    <p class="text-retro-muted mb-6 flex-grow text-sm leading-relaxed">
        {{ project.description or "Sem descrição disponível." }}
    </p>
    <div class="mt-auto flex justify-between items-center pt-4 border-t border-white/5">
        <span class="text-xs text-retro-secondary font-mono">{{ project.language or "Code" }}</span>
        <a href="{{ project.url }}" target="_blank"
            class="text-white hover:text-retro-accent text-sm font-semibold flex items-center gap-1 transition-colors">
            Ver Código
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24"
                stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
        </a>
    </div>
</div>
{% endfor %}

{% if next_page %}
<div id="load-more-container" class="col-span-1 md:col-span-2 lg:col-span-3 flex justify-center mt-8">
    <button hx-get="/projects/more?page={{ next_page }}" hx-trigger="click" hx-target="#load-more-container"
        hx-swap="outerHTML"
        class="bg-retro-card border border-white/10 text-white px-6 py-3 rounded-lg font-mono text-sm hover:bg-white/5 transition-colors flex items-center gap-2">
        <span>[ CARREGAR MAIS ]</span>
        <img class="htmx-indicator h-5 w-5"
            src="https://raw.githubusercontent.com/n3r4zzurr0/svg-spinners/main/svg-css/90-ring-with-bg.svg"
            alt="Loading...">
    </button>
</div>
{% endif %}
```

## File: app\templates\partials\contact_success.html
```html
<div class="bg-green-900/20 border border-green-500/30 rounded-xl p-6 text-center animate-fade-in">
    <div class="inline-flex items-center justify-center w-12 h-12 rounded-full bg-green-500/20 mb-4">
        <svg class="w-6 h-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
        </svg>
    </div>
    <h3 class="text-lg font-bold text-green-400 mb-2">Mensagem Recebida!</h3>
    <p class="text-green-200/80">Obrigado, {{ name }}. Entrarei em contato em breve.</p>
</div>
```

## File: requirements.txt
```
fastapi
uvicorn
sqlmodel
asyncpg
jinja2
httpx
python-multipart
python-dotenv
aiosqlite

```

## File: tests\run_tests.py
```python
import unittest
import httpx
import asyncio
import sys
import os

# Add parent directory to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

class TestPortfolio(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        transport = httpx.ASGITransport(app=app)
        self.client = httpx.AsyncClient(transport=transport, base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_read_root(self):
        """Test if the root endpoint returns 200 and correct content."""
        response = await self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("DevFolio", response.text)
        print("✅ Root endpoint (/) passed")

    async def test_api_status(self):
        """Test if the status endpoint returns 200 and online status."""
        response = await self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "online")
        print("✅ API Status (/api/status) passed")

    async def test_projects_sync(self):
        """Test if project sync returns 200."""
        response = await self.client.get("/projects/sync")
        self.assertEqual(response.status_code, 200)
        print("✅ Project Sync (/projects/sync) passed")

    async def test_404_handling(self):
        """Test how the app handles non-existent routes."""
        response = await self.client.get("/non-existent-route")
        self.assertEqual(response.status_code, 404)
        print(f"ℹ️ 404 Response: {response.json()}")
        if response.json().get("detail") == "Not Found":
             print("✅ Standard 404 handling confirmed")

if __name__ == "__main__":
    unittest.main(verbosity=2)

```

