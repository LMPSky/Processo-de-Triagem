from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "configs"


def ensure_default_configs() -> bool:
    """
    Cria a pasta configs/ se não existir.

    ⚠️ IMPORTANTE: Os arquivos JSON devem ser criados MANUALMENTE
    ou copiados de um backup/template na primeira execução.

    Este script apenas garante que a pasta existe.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    required_files = [
        "trabalhista_categorias.json",
        "civel_priority_names.json",
        "civel_priority_clients.json",
        "civel_excludentes.json",
        "civel_numero_patterns.json",
        "civel_categorias.json",
        "civel_macrocategorias.json",
        "client_aliases.json",
    ]

    missing_files = [f for f in required_files if not (CONFIG_DIR / f).exists()]

    if missing_files:
        print("\n⚠️  ARQUIVOS DE CONFIGURAÇÃO FALTANDO:")
        for f in missing_files:
            print(f"   • {f}")
        print(f"\n💡 Copie os arquivos JSON para a pasta: {CONFIG_DIR.resolve()}")
        print("   Ou crie-os manualmente com as respectivas configurações.\n")
        return False

    print(f"✅ Todos os arquivos de configuração encontrados em: {CONFIG_DIR.resolve()}\n")
    return True


if __name__ == "__main__":
    success = ensure_default_configs()
    if not success:
        print("⚠️  Configuração incompleta. Por favor, adicione os arquivos faltantes.\n")