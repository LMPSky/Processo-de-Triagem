# Processo Triage

Aplicação para triagem de processos com interface gráfica, comparação contra a base Legal One, separação entre fluxos trabalhista e cível, categorização, priorização, geração de relatórios Excel, auditoria por execução e histórico comparativo entre rodadas.

---

## Sumário

- [Visão geral](#visão-geral)
- [Principais funcionalidades](#principais-funcionalidades)
- [Arquitetura em alto nível](#arquitetura-em-alto-nível)
- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Configurações](#configurações)
- [Como executar](#como-executar)
  - [1. Interface gráfica](#1-interface-gráfica)
  - [2. Pipeline principal](#2-pipeline-principal)
- [Fluxo operacional da interface](#fluxo-operacional-da-interface)
- [Estrutura de saída](#estrutura-de-saída)
- [Auditoria da execução](#auditoria-da-execução)
- [Histórico e comparações](#histórico-e-comparações)
- [Logs](#logs)
- [Testes](#testes)
- [Organização técnica](#organização-técnica)
- [Troubleshooting](#troubleshooting)
- [Boas práticas de manutenção](#boas-práticas-de-manutenção)
- [Sugestões de uso](#sugestões-de-uso)
- [Melhorias já incorporadas](#melhorias-já-incorporadas)
- [Execução rápida](#execução-rápida)

---

## Visão geral

O **Processo Triage** é um robô de triagem de processos com foco operacional, pensado para:

- comparar bases externas contra a base **Legal One**;
- separar processos entre cenários com e sem match;
- classificar processos cíveis e trabalhistas;
- priorizar casos conforme regras de negócio;
- gerar relatórios e consolidados em Excel;
- registrar auditoria detalhada por execução;
- manter histórico técnico e comparativo entre rodadas.

O projeto possui **dois modos principais de uso**:

### Interface gráfica
Modo recomendado para operação diária.

Permite:
- seleção de arquivos por tipo de base;
- acompanhamento visual da execução;
- barra de progresso e logs em tempo real;
- resumo executivo pós-processamento;
- abertura rápida de resultado, auditoria e histórico.

### Pipeline principal
Modo mais direto, utilizado quando já se deseja executar o processamento com os arquivos previamente preparados na pasta `input/`.

---

## Principais funcionalidades

- comparação da base externa com a base Legal One;
- separação entre:
  - processos com match;
  - processos sem match trabalhista;
  - processos sem match cível;
- classificação trabalhista;
- classificação cível;
- priorização por regras, aliases e sinais;
- geração de relatórios Excel;
- auditoria detalhada por execução;
- histórico técnico consolidado;
- comparação com execução anterior;
- comparação com média de execuções recentes;
- resumo executivo na interface;
- modo diagnóstico para preservar evidências adicionais da execução;
- organização automática dos resultados mais recentes e históricos.

---

## Arquitetura em alto nível

A aplicação está organizada em camadas simples e objetivas:

### 1. Interface (`ui/`)
Responsável por:
- seleção de arquivos;
- interação com o usuário;
- visualização de progresso;
- exibição de logs;
- apresentação do resumo executivo;
- navegação para resultados e artefatos.

### 2. Handler de execução
O `ProcessHandler` faz a orquestração do fluxo:
- prepara arquivos de entrada;
- executa o pipeline principal;
- registra logs;
- constrói auditoria;
- persiste histórico;
- devolve o resumo para a interface.

### 3. Pipeline principal
Responsável pela lógica de leitura, matching, classificação e exportação.

### 4. Serviços auxiliares
Módulos especializados tratam:
- histórico;
- auditoria;
- input;
- fontes;
- sanitização e preparação de dados.

---

## Requisitos

- Python 3.10+
- dependências listadas em `requirements.txt`

---

## Instalação

```bash
pip install -r requirements.txt
```

---

## Estrutura do projeto

Estrutura simplificada esperada:

```text
processo_triage/
├─ app.py
├─ main.py
├─ config.py
├─ matcher.py
├─ reader.py
├─ filters.py
├─ number_extractor.py
├─ logger.py
├─ bootstrap_configs.py
├─ configs/
├─ input/
├─ output/
├─ logs/
├─ logs_ui/
├─ ui/
├─ classifiers/
├─ reporting/
├─ tests/
└─ requirements.txt
```

### Pastas importantes

#### `configs/`
Arquivos JSON com regras de classificação, aliases, categorias, prioridades e listas auxiliares.

#### `input/`
Arquivos preparados para processamento pelo pipeline principal.

#### `output/`
Resultados atuais, snapshots por execução e histórico técnico.

#### `logs/`
Logs do pipeline principal.

#### `logs_ui/`
Logs gerados pela interface gráfica e pelo fluxo assistido.

#### `ui/`
Componentes da interface, widgets, handlers e services auxiliares.

#### `classifiers/`
Classificadores cível e trabalhista, além de normalizadores e utilitários ligados à classificação.

#### `reporting/`
Geração de resumos, análises e relatórios auxiliares.

#### `tests/`
Suíte automatizada com testes de services, handlers, helpers e fluxos críticos.

---

## Configurações

Antes de executar, garanta que a pasta `configs/` contenha os arquivos JSON esperados pelo projeto.

Para validar ou criar a estrutura mínima:

```bash
python bootstrap_configs.py
```

### Exemplos de arquivos esperados em `configs/`

- `trabalhista_categorias.json`
- `civel_priority_names.json`
- `civel_priority_clients.json`
- `civel_excludentes.json`
- `civel_numero_patterns.json`
- `civel_categorias.json`
- `civel_macrocategorias.json`
- `client_aliases.json`

> O script de bootstrap garante a existência da pasta, mas os conteúdos dos arquivos precisam existir corretamente no ambiente.

---

## Como executar

## 1. Interface gráfica

Forma recomendada de uso:

```bash
python app.py
```

### O que a interface permite

- selecionar arquivos por tipo de base;
- marcar fontes opcionais como ausentes;
- executar em modo diagnóstico;
- acompanhar progresso e logs em tempo real;
- visualizar resumo executivo da execução;
- abrir rapidamente:
  - resultado atual;
  - histórico de resultados;
  - pasta da auditoria;
  - resumo markdown;
  - log da execução;
  - histórico técnico.

---

## 2. Pipeline principal

Para executar diretamente o pipeline:

```bash
python main.py
```

> Nesse modo, os arquivos necessários já devem estar corretamente preparados em `input/`, conforme as regras do `config.py`.

---

## Fluxo operacional da interface

A interface foi desenhada para reduzir a necessidade de trabalho manual com nomes de arquivos e limpeza de diretórios.

### Fluxo esperado

1. selecionar cada base no bloco correspondente;
2. iniciar o processamento;
3. acompanhar a barra de progresso e os logs;
4. revisar o resumo executivo;
5. abrir o resultado atual, auditoria ou histórico, se necessário.

### Regras importantes

- a base **Legal One** é obrigatória;
- as demais bases podem ser:
  - informadas;
  - ou marcadas como ausentes na execução;
- não é necessário renomear manualmente os arquivos para uso pela UI;
- não é necessário limpar manualmente a pasta `input/` antes de rodar.

---

## Estrutura de saída

A saída foi reorganizada para evitar confusão entre resultados antigos e atuais.

```text
output/
├─ latest/
├─ runs/
│  ├─ 20260429_101500/
│  ├─ 20260429_143200/
└─ _historico_execucoes/
```

### `output/latest/`
Contém o resultado mais recente disponível para consulta operacional rápida.

### `output/runs/<timestamp>/`
Contém o snapshot completo de cada execução.

Exemplo:

```text
output/runs/20260429_143200/
├─ arquivos_excel_gerados...
└─ _auditoria/
   ├─ resumo_execucao.json
   ├─ resumo_execucao.md
   ├─ fontes_utilizadas.json
   ├─ arquivos_saida.json
   ├─ comparativo_execucao_anterior.json
   ├─ comparativo_media_ultimas_execucoes.json
   ├─ alertas_execucao.json
   └─ outros artefatos auxiliares
```

### `output/_historico_execucoes/`
Histórico técnico consolidado das execuções, em CSV e/ou Excel.

---

## Auditoria da execução

Cada execução gera artefatos para facilitar análise posterior e rastreabilidade.

### Exemplos de artefatos

- resumo da execução em JSON;
- resumo da execução em Markdown;
- log da execução;
- fontes utilizadas;
- índice de arquivos de saída;
- comparativo com execução anterior;
- comparativo com média recente;
- observações operacionais;
- consolidados auxiliares de auditoria.

### Modo diagnóstico

Quando ativado na UI, o modo diagnóstico preserva evidências adicionais da execução, incluindo snapshot dos arquivos de entrada na pasta de auditoria.

---

## Histórico e comparações

O projeto mantém histórico técnico de execuções para fins comparativos.

### Atualmente, a comparação é usada para:

- mostrar variações em relação à execução anterior;
- mostrar variações em relação à média recente;
- produzir observações operacionais;
- enriquecer o resumo executivo da interface.

### Interpretação recomendada

Essas comparações devem ser lidas como **informação operacional**, e não necessariamente como falha do robô.

Oscilações em:
- volume processado;
- quantidade de arquivos gerados;
- quantidade de `sem_match`;

podem refletir apenas mudanças naturais nas bases recebidas.

---

## Logs

### Logs do pipeline principal
Gerados em:

```text
logs/
```

### Logs da interface
Gerados em:

```text
logs_ui/
```

Os logs da UI registram, entre outros:
- etapas do processamento;
- saída padrão do pipeline;
- mensagens de erro;
- caminho da auditoria;
- caminho do log da execução.

---

## Testes

Para executar toda a suíte:

```bash
python -m pytest -q
```

Para executar um arquivo específico:

```bash
python -m pytest tests/test_handlers_process.py -q
```

### Cobertura já existente no projeto

- services de auditoria;
- services de histórico;
- services de input;
- services de fontes;
- sanitização e tratamento de arquivos;
- widgets e helpers visuais;
- fluxo principal do handler;
- cenários de sucesso e erro no `_process()`.

---

## Organização técnica

### Interface (`ui/`)
Responsável por:
- seleção de arquivos;
- callbacks de progresso;
- logs visuais;
- resumo executivo;
- navegação para resultado, auditoria e histórico.

### `ProcessHandler`
Responsável por:
- preparar inputs;
- executar o pipeline;
- construir auditoria;
- persistir histórico;
- montar o resumo final entregue à UI.

### `ExecutionHistoryService`
Responsável por:
- histórico de execuções;
- comparações entre rodadas;
- observações operacionais;
- resumo de tendências.

### `AuditService`
Responsável por:
- geração de arquivos de auditoria;
- consolidados auxiliares;
- resumo em Markdown e JSON.

### `InputService`
Responsável por:
- limpeza controlada do input;
- cópia e preparação dos arquivos selecionados;
- snapshot das entradas em modo diagnóstico.

---

## Troubleshooting

### 1. A interface abre, mas o processamento não inicia
Verifique:
- se a base Legal One foi informada;
- se os arquivos selecionados estão nos blocos corretos;
- se há mensagens de validação na interface.

### 2. O pipeline falha por arquivo não encontrado
Verifique:
- se os arquivos esperados realmente chegaram ao `input/`;
- se as configurações do `config.py` estão coerentes;
- se a preparação das entradas foi concluída sem erro.

### 3. O Excel não é gerado ou falha ao salvar
Verifique:
- se algum arquivo gerado anteriormente está aberto no Excel;
- se há permissão de escrita nas pastas `output/`, `logs/` e `logs_ui/`.

### 4. O resultado parece diferente da execução anterior
Nem toda variação indica problema técnico. Oscilações podem refletir:
- mudança no volume das bases;
- mudança no conteúdo das entradas;
- mudança natural de distribuição entre match e sem match.

### 5. O histórico não aparece como esperado
Verifique se:
- a execução chegou ao fim com registro de auditoria;
- a pasta `output/_historico_execucoes/` está preservada;
- os arquivos de output não estão sendo removidos manualmente de forma indevida.

---

## Boas práticas de manutenção

- prefira alterar regras de classificação nos JSONs de `configs/` antes de alterar código;
- ao mudar comportamento de classificação, atualize também os testes;
- ao alterar estrutura de saída, atualize esta documentação;
- use a interface gráfica como caminho padrão para operação;
- preserve as pastas de histórico e auditoria entre execuções.

---

## Sugestões de uso

- use a **interface gráfica** como entrada padrão para operação;
- use `output/latest/` para acessar rapidamente o último resultado;
- use `output/runs/` quando precisar revisar uma execução específica;
- use a pasta `_auditoria/` da execução quando precisar investigar comportamento, tendências ou saídas;
- use o modo diagnóstico apenas quando precisar ampliar a rastreabilidade da rodada.

---

## Melhorias já incorporadas

- interface gráfica com seleção por tipo de base;
- drag-and-drop de arquivos;
- resumo executivo pós-execução;
- botões para abertura rápida de artefatos;
- auditoria por execução;
- histórico técnico consolidado;
- comparação com execução anterior;
- comparação com média recente;
- classificação cível modularizada;
- classificação trabalhista modularizada;
- listas e regras movidas para JSON em `configs/`;
- testes automatizados com `pytest`;
- estrutura de saída com `latest/` e `runs/`.

---

## Execução rápida

### Subir interface
```bash
python app.py
```

### Rodar pipeline direto
```bash
python main.py
```

### Rodar testes
```bash
python -m pytest -q
```