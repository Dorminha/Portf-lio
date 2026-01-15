import httpx
import logging
from typing import List, Optional
from app.models import Project
from app.core.config import get_settings

# Configura o logger padrão da aplicação
logger = logging.getLogger(__name__)

class GitHubService:
    """
    Serviço responsável por interagir com a API do GitHub.
    
    PADRÃO DE USO:
    Esta classe DEVE ser usada como um Context Manager para garantir
    que a conexão HTTP seja fechada corretamente.
    
    Exemplo:
        async with GitHubService() as service:
            projects = await service.fetch_projects()
    """
    BASE_URL = "https://api.github.com"
    TIMEOUT = 10.0

    def __init__(self):
        self.settings = get_settings()
        self.username = self.settings.GITHUB_USERNAME
        self.token = self.settings.GITHUB_TOKEN
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """
        Inicia a sessão HTTP (Connection Pool).
        """
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": f"{self.settings.APP_NAME}-SyncService"
        }
        
        if self.token:
            headers["Authorization"] = f"token {self.token}"
            
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL, 
            headers=headers, 
            timeout=self.TIMEOUT
        )
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """
        Fecha a sessão HTTP e libera recursos do sistema.
        """
        if self.client:
            await self.client.aclose()

    def _ensure_client(self) -> httpx.AsyncClient:
        """
        Garante que o cliente HTTP foi inicializado.
        Previne uso incorreto da classe sem 'async with'.
        """
        if not self.client:
            raise RuntimeError(
                "GitHubService deve ser usado dentro de um bloco 'async with' para gerenciar conexões."
            )
        return self.client

    async def fetch_projects(self) -> List[Project]:
        """
        Busca repositórios públicos, excluindo forks e projetos sem descrição.
        """
        client = self._ensure_client()
        
        try:
            # Query params otimizados
            params = {
                "sort": "updated", 
                "per_page": 100, 
                "type": "owner"
            }
            
            response = await client.get(f"/users/{self.username}/repos", params=params)
            response.raise_for_status()
            repos = response.json()

            projects = []
            for repo in repos:
                # Regras de Negócio (Filtros)
                if repo.get("fork") is True:
                    continue
                
                if not repo.get("description"):
                    continue

                # Opcional: Filtrar por Tópico (Ex: apenas projetos com tag 'portfolio')
                # topics = repo.get("topics", [])
                # if "portfolio" not in topics: continue

                # Tratamento de dados nulos (Language pode ser None no GitHub)
                language = repo.get("language") or "Geral"

                project = Project(
                    name=repo["name"],
                    description=repo["description"],
                    url=repo["html_url"],
                    stars=repo["stargazers_count"],
                    language=language 
                )
                projects.append(project)
            
            # Ordenação por relevância (estrelas)
            projects.sort(key=lambda x: x.stars, reverse=True)
            
            logger.info(f"Sincronização GitHub: {len(projects)} projetos processados com sucesso.")
            return projects

        except httpx.HTTPStatusError as e:
            logger.error(f"Erro HTTP GitHub: {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            logger.exception("Erro crítico ao buscar projetos do GitHub.")
            return []

    async def fetch_readme(self, repo_name: str) -> Optional[str]:
        """
        Busca o conteúdo cru (RAW) do README.md.
        """
        client = self._ensure_client()
        
        # Header específico para receber texto puro em vez de JSON base64
        headers = {"Accept": "application/vnd.github.v3.raw"}
        
        try:
            response = await client.get(
                f"/repos/{self.username}/{repo_name}/readme",
                headers=headers
            )
            
            if response.status_code == 404:
                # Log warning em vez de error, pois é comum não ter README
                logger.warning(f"README ausente para o repositório: {repo_name}")
                return None
                
            response.raise_for_status()
            return response.text
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Erro ao baixar README de '{repo_name}': {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado no README de '{repo_name}': {str(e)}")
            return None