<div align="center">

# Extrator de Substantivos em PDFs

Notebook do Google Colab (e módulo Python) que lê arquivos PDF em português, identifica
**substantivos comuns** e **nomes próprios** com Processamento de Linguagem Natural e
exporta o resultado para **CSV/XLSX**.

[![Abrir no Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/S1l45S/ExtratorSubstantivo/blob/main/notebooks/extrator_substantivos.ipynb)

</div>

---

## Como funciona

| Etapa | Ferramenta | O que faz |
|---|---|---|
| 1. Leitura | `pypdf` (padrão) ou `pdfplumber` | Converte cada página do PDF em texto |
| 2. Limpeza | `limpar_texto()` | Junta palavras hifenizadas, troca ligaduras, normaliza espaços |
| 3. Análise gramatical | `spaCy` + modelo `pt_core_news_*` | *Part-of-Speech tagging*: classifica cada palavra |
| 4. Filtro | `NOUN` e `PROPN` | Mantém só substantivos (comuns e próprios) |
| 5. Consolidação | `pandas` | Agrupa termos com frequência e páginas onde aparecem |
| 6. Saída | CSV (`;`, UTF-8) e/ou XLSX | Salva na pasta `saida` do Google Drive |

---

## Uso rápido (Google Colab)

1. Crie a conta Google do projeto e, no Drive, a pasta `ExtratorSubstantivos/entrada`.
2. Coloque os PDFs em `entrada`.
3. Abra o notebook `notebooks/extrator_substantivos.ipynb` no Colab.
4. Ajuste os campos interativos (célula **3. Parâmetros**).
5. **Ambiente de execução → Executar tudo** (ou `Ctrl + F9`).
6. Pegue os arquivos em `ExtratorSubstantivos/saida`.

Passo a passo detalhado: [`GUIA_COLAB.md`](docs/GUIA_COLAB.md).

---

### Parâmetros do notebook

| Campo | Padrão | Descrição |
|---|---|---|
| `pasta_base` | `/content/drive/MyDrive/ExtratorSubstantivos` | Pasta do Drive com `entrada/` e `saida/` |
| `arquivo` | `todos` | Nome de um PDF específico ou `todos` |
| `modelo` | `pt_core_news_sm` | `sm` (rápido), `md`, `lg` (mais preciso) |
| `incluir_nomes_proprios` | `True` | Inclui `PROPN` além de `NOUN` |
| `usar_forma_de_dicionario` | `False` | Reduz *casas → casa* (lematização) |
| `min_caracteres` | `3` | Descarta termos mais curtos |
| `motor_pdf` | `pypdf` | Alternativa: `pdfplumber` (melhor em tabelas/colunas) |
| `formato_saida` | `ambos` | `csv`, `xlsx` ou `ambos` |

---

### Exemplo de saída

| arquivo | termo | classe | frequencia | paginas |
|---|---|---|---|---|
| relatorio.pdf | saúde | NOUN | 42 | 1, 2, 5, 9 |
| relatorio.pdf | Aracaju | PROPN | 7 | 1, 3 |

O XLSX traz duas abas: `substantivos` (por arquivo) e `resumo_geral` (soma de todos os PDFs).

---

## Uso local (opcional)

```bash
python -m venv .venv 
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download pt_core_news_sm
python src/extrator_substantivos.py data/entrada -o data/saida --formato ambos
```

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```

Os testes usam um modelo spaCy simulado (rápidos, sem download) e PDFs gerados na hora.

---

## Estrutura do repositório

```
├── notebooks/extrator_substantivos.ipynb   # notebook do Colab (gerado, não editar à mão)
├── src/extrator_substantivos.py            # lógica única, usada pelo notebook e pela CLI
├── tools/build_notebook.py                 # gera o notebook a partir de src/
├── tests/                                  # testes automatizados (pytest)
├── docs/                                   # arquitetura e guia do Colab
├── data/entrada, data/saida                # pastas para uso local (conteúdo ignorado pelo Git)
├── COMMITS.md                              # sugestão de commits e fluxo de trabalho
├── requirements.txt / requirements-dev.txt
└── README.md
```
---

## Limitações conhecidas

- **PDFs escaneados** (imagem) não têm texto: o programa avisa e pula o arquivo. Seria
  preciso OCR (ex.: Tesseract) como etapa extra.
- O *tagger* do spaCy erra em textos técnicos, siglas e caixa-alta; revise a saída quando
  precisão importar. Modelos `md`/`lg` erram menos que o `sm`.
- A junção de palavras quebradas por hífen (`infor-\nmação`) pode unir indevidamente
  compostos escritos com hífen no fim da linha (`guarda-\nchuva`).
- Colunas e tabelas podem embaralhar a ordem do texto; teste `pdfplumber` nesses casos.

Mais detalhes em [`ARQUITETURA.md`](docs/ARQUITETURA.md).
