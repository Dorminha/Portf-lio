from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager

from app.database import init_db
from app.core.config import get_settings
from app.core.i18n import get_translations
# CORREÇÃO AQUI: Removido o chat duplicado
from app.routers import general, projects, blog, admin, chat 
from app.services.steam_service import close_client as close_steam_client

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_steam_client()

settings = get_settings()

app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

@app.middleware("http")
async def i18n_middleware(request: Request, call_next):
    lang = request.cookies.get("lang", "pt")
    request.state.lang = lang
    request.state.trans = get_translations(lang)
    response = await call_next(request)
    return response

# Static Files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Routers
app.include_router(general.router)
app.include_router(projects.router)
app.include_router(blog.router)
app.include_router(admin.router)
app.include_router(chat.router) # O main.py está chamando o router corretamente aqui.


# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response