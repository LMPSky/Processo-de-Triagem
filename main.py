"""Ponto de entrada do sistema de triagem de processos."""
from config import get_config
from matcher import run_matching

def main() -> None:
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║       TRIAGEM DE PROCESSOS — Legal One           ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    config = get_config()
    run_matching(config)

    print()
    print("✅ Processo concluído com sucesso!")
    print()


if __name__ == "__main__":
    main()