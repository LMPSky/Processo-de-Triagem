from __future__ import annotations

import sys
from config import get_config
from matcher import run_matching
from logger import setup_logger

def main() -> None:
    setup_logger()
    log = setup_logger(__name__)

    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║       TRIAGEM DE PROCESSOS — Legal One           ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    try:
        config = get_config()

        if not config.print_validation():
            log.error("Validação falhou — abortando execução.")
            sys.exit(1)
            print("WebJur config:", config.webjur.__dict__ if hasattr(config.webjur, '__dict__') else config.webjur)

        run_matching(config)

        print()
        log.info("✅ Processo concluído com sucesso!")
        print()

    except FileNotFoundError as e:
        print()
        log.error("Arquivo não encontrado: %s", e)
        print()
        print("💡 Verifique se os arquivos de entrada estão na pasta 'input/'")
        print("   e se os nomes conferem com o config.py.")
        sys.exit(1)

    except ValueError as e:
        print()
        log.error("Dados inválidos: %s", e)
        print()
        print("💡 Verifique se as colunas dos arquivos estão corretas")
        print("   e se o formato (xlsx/csv) está de acordo com o config.py.")
        sys.exit(1)

    except PermissionError as e:
        print()
        log.error("Sem permissão de acesso: %s", e)
        print()
        print("💡 Feche os arquivos Excel que possam estar abertos")
        print("   e verifique as permissões da pasta 'output/'.")
        sys.exit(1)

    except KeyboardInterrupt:
        print()
        log.warning("Execução interrompida pelo usuário.")
        sys.exit(130)

    except Exception as e:
        print()
        log.exception("Erro inesperado (%s): %s", type(e).__name__, e)
        print()
        print("💡 Se o problema persistir, verifique:")
        print("   1. Os arquivos de entrada estão na pasta correta?")
        print("   2. Os nomes das colunas conferem com o config.py?")
        print("   3. Algum arquivo Excel está aberto?")
        sys.exit(1)


if __name__ == "__main__":
    main()