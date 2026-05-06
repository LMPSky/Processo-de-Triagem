"""
Configuração da aplicação.
"""
from pathlib import Path

class AppConfig:
    """Configurações da aplicação."""
    
    def __init__(self):
        # Pasta raiz do projeto
        self.root_dir = Path(__file__).parent
        
        # Pastas de entrada e saída
        self.input_dir = self.root_dir / "input"
        self.output_dir = self.root_dir / "output"
        
        # Criar pastas se não existirem
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
    
    @property
    def input_path(self):
        """Retorna caminho de entrada."""
        return str(self.input_dir)
    
    @property
    def output_path(self):
        """Retorna caminho de saída."""
        return str(self.output_dir)