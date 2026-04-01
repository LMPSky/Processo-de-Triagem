# Processo de Triagem — Legal One

Sistema de triagem automatizada de processos jurídicos. Lê processos de 3 fontes externas (Painel, DW, WebJur), compara com a base Legal One, classifica por categorias e exporta relatórios organizados.

> 🤖 **Este projeto foi desenvolvido com auxílio do GitHub Copilot (@copilot).**


## Funcionalidades

- **Leitura multi-fonte**: Painel (Excel), DW (Excel), WebJur (CSV) com detecção automática de encoding
- **Comparação com Legal One**: Identifica processos que já estão cadastrados (COM match = nossos)
- **Classificação por categoria**: Busca termos no texto das intimações para separar por tipo processual
- **Destaque Décio Freire**: Processos do escritório são marcados como PRIORIDADE
- **Filtros avançados**:
  - Extração de UF e Ramo da Justiça do CNJ
  - Validação de dígito verificador
  - Identificação de processos antigos (antes de 2015)
  - Remoção de duplicatas entre fontes
  - Análise de presença em múltiplas fontes

## Estrutura

```
processo_triage/
├── main.py                 # Ponto de entrada
├── config.py               # Configurações das fontes
├── reader.py               # Leitura de arquivos (Excel/CSV)
├── number_extractor.py     # Extração e normalização de números CNJ
├── filters.py              # Filtros (dedup, UF, dígito, idade)
├── categorizer.py          # Classificação por categoria (texto)
├── matcher.py              # Orquestrador principal
├── requirements.txt
├── input/                  # Arquivos de entrada (não versionados)
└── output/                 # Arquivos de saída (não versionados)
    ├── ⭐ PRIORIDADE_decio_freire_xxx.xlsx
    ├── com_match_geral_xxx.xlsx
    ├── lixo_sem_match_xxx.xlsx
    ├── duplicados_removidos_xxx.xlsx
    ├── processos_antigos_xxx.xlsx
    ├── resumo_xxx.txt
    └── categorias/
        ├── cumprimento_de_sentenca_xxx.xlsx
        ├── mandado_de_seguranca_xxx.xlsx
        └── ...
```

## Instalação

```bash
pip install -r requirements.txt
```

## Configuração

Antes de rodar, edite o `config.py` e ajuste os caminhos para o seu ambiente:

```python
input_dir: str = r"C:\caminho\para\sua\pasta\input"
output_dir: str = r"C:\caminho\para\sua\pasta\output"
```

## Uso

1. Coloque os arquivos de entrada na pasta `input/`
2. Execute:

```bash
python main.py
```

3. Os resultados estarão na pasta `output/`

## Categorias

| Categoria | Termos de busca |
|-----------|----------------|
| Ação de Cumprimento | ACum, ACIA, Ação de Cumprimento... |
| Carta Precatória | CartPrec, CartPrecCiv, CPre... |
| Conflito de Competência | CCCiv... |
| Cumprimento de Sentença | CumSen, CumPrSe, CumSenFaz... |
| Décio Freire | Decio Freire, Décio Flávio Gonçalves... |
| Execução de Certidão de Crédito Judicial | ExCCj... |
| Execução de Título Extrajudicial | ExTiEx... |
| Execução Fiscal | ExFis, Cautelar Fiscal... |
| Execução Provisória | ExProvAS... |
| Mandado de Segurança | MSCiv, MSCi... |
| Recurso de Julgamento Parcial | tema 1046, Ofício Circular AR... |
| TRT 14 - Contrato GPA | SCB DISTR, Comprebem... |
| Tutela Cautelar Antecedente | TutCautAnt... |

## Fluxo

```
Bases externas (Painel + DW + WebJur)
    │
    ▼
Remover duplicatas
    │
    ▼
Extrair detalhes CNJ (UF, Ramo, Ano)
    │
    ▼
Validar dígito verificador
    │
    ▼
Comparar com Legal One
    │
    ├── COM match (nossos) → Classificar por categoria
    │     ├── ⭐ Décio Freire → PRIORIDADE
    │     ├── Categorias específicas → 1 arquivo cada
    │     └── Sem categoria → com_match_geral.xlsx
    │
    └── SEM match → lixo_sem_match.xlsx
```

## Créditos

- Desenvolvido com auxílio do [GitHub Copilot](https://github.com/features/copilot)
- Direitos reservados a **Décio Freire Advogados**
