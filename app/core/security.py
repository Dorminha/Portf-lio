from passlib.context import CryptContext

class PasswordHandler:
    """
    Classe utilitária para manipulação de hashes de senha.
    Encapsula a lógica do passlib para facilitar testes e manutenção.
    """
    
    def __init__(self):
        # Argon2id é atualmente o padrão-ouro para hashing de senhas.
        # Ele é resistente a ataques de força bruta usando GPUs.
        self._context = CryptContext(schemes=["argon2"], deprecated="auto")

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Verifica a validade da senha."""
        if not plain_password or not hashed_password:
            return False
        return self._context.verify(plain_password, hashed_password)

    def hash(self, password: str) -> str:
        """Cria um hash seguro da senha."""
        return self._context.hash(password)

# Instância Singleton para ser importada e usada
password_handler = PasswordHandler()

# Funções wrappers para manter compatibilidade com a interface funcional se preferir,
# ou você pode injetar a classe PasswordHandler como dependência.
def verify_password(plain: str, hashed: str) -> bool:
    return password_handler.verify(plain, hashed)

def get_password_hash(password: str) -> str:
    return password_handler.hash(password)