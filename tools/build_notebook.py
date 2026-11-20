"""Gera notebooks/extrator_substantivos.ipynb a partir de src/extrator_substantivos.py.

Assim o código do notebook e o código testado são sempre o mesmo.
Uso:  python tools/build_notebook.py
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
FONTE = RAIZ / "src" / "extrator_substantivos.py"
DESTINO = RAIZ / "notebooks" / "extrator_substantivos.ipynb"
MARCADOR_CLI = "# --- CLI ---"


def md(texto: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": texto.strip("\n").splitlines(True)}


def code(texto: str, **meta) -> dict:
    return {
        "cell_type": "code",
        "metadata": meta,
        "execution_count": None,
        "outputs": [],
        "source": texto.strip("\n").splitlines(True),
    }


def codigo_do_modulo() -> str:
    fonte = FONTE.read_text(encoding="utf-8")
    return fonte.split(MARCADOR_CLI)[0].rstrip() + "\n"


CELULAS = [
    md("""
# Extrator de substantivos em PDFs (pt-BR)

Lê PDFs de uma pasta do Google Drive, identifica **substantivos comuns (NOUN)** e
**nomes próprios (PROPN)** com spaCy e salva a lista em CSV/Excel.

**Como usar**
1. Coloque os PDFs na pasta `entrada` do Drive (veja a célula 3).
2. Ajuste os parâmetros na célula 3 (campos interativos).
3. Menu **Ambiente de execução → Executar tudo** (ou `Ctrl + F9`).
4. Os resultados aparecem na pasta `saida` do Drive.
"""),
    md("## 1. Instalação (deixe sempre no topo)"),
    code(
        "!pip install -q pypdf pdfplumber spacy pandas openpyxl",
        cellView="form",
    ),
    md("## 2. Conectar ao Google Drive"),
    code(
        '''
try:
    from google.colab import drive
    drive.mount("/content/drive")
except ImportError:
    print("Fora do Colab: usando o sistema de arquivos local.")
'''
    ),
    md("""
## 3. Parâmetros
Altere apenas esta célula. Para processar um PDF específico, digite o nome dele
(ex.: `relatorio.pdf`); deixe `todos` para processar a pasta inteira.
"""),
    code(
        '''
#@title Parâmetros { display-mode: "form" }
pasta_base = "/content/drive/MyDrive/ExtratorSubstantivos" #@param {type:"string"}
arquivo = "todos" #@param {type:"string"}
modelo = "pt_core_news_sm" #@param ["pt_core_news_sm", "pt_core_news_md", "pt_core_news_lg"]
incluir_nomes_proprios = True #@param {type:"boolean"}
usar_forma_de_dicionario = False #@param {type:"boolean"}
min_caracteres = 3 #@param {type:"slider", min:1, max:10, step:1}
motor_pdf = "pypdf" #@param ["pypdf", "pdfplumber"]
formato_saida = "ambos" #@param ["csv", "xlsx", "ambos"]
''',
        cellView="form",
    ),
    md("## 4. Funções (não precisa editar)\nCódigo gerado de `src/extrator_substantivos.py`."),
    code(codigo_do_modulo()),
    md("## 5. Executar"),
    code(
        '''
from IPython.display import display

base = Path(pasta_base)
pasta_entrada, pasta_saida = base / "entrada", base / "saida"
pasta_entrada.mkdir(parents=True, exist_ok=True)
pasta_saida.mkdir(parents=True, exist_ok=True)

if arquivo.strip().lower() in ("", "todos") and not listar_pdfs(pasta_entrada):
    print(f"Nenhum PDF encontrado em: {pasta_entrada}\\nCopie os arquivos para lá e execute novamente.")
else:
    print(f"Carregando modelo {modelo}...")
    nlp = carregar_modelo(modelo)

    df, falhas = processar_pasta(
        pasta_entrada,
        nlp,
        arquivo=arquivo,
        motor=motor_pdf,
        classes=CLASSES_PADRAO if incluir_nomes_proprios else ("NOUN",),
        usar_lema=usar_forma_de_dicionario,
        min_caracteres=min_caracteres,
    )

    for nome, motivo in falhas:
        print(f"[aviso] {nome}: {motivo}")

    if df.empty:
        print("Nenhum substantivo extraído.")
    else:
        nome_base = Path(arquivo).stem if arquivo.strip().lower() not in ("", "todos") else "substantivos"
        for caminho in salvar_resultados(df, pasta_saida, nome_base, formato_saida):
            print(f"Gerado: {caminho}")
        print(f"\\n{len(df)} termos distintos em {df['arquivo'].nunique()} arquivo(s).")
'''
    ),
    md("## 6. Prévia dos resultados"),
    code(
        '''
if "df" in globals() and not df.empty:
    display(resumo_geral(df).head(30))
'''
    ),
]

NOTEBOOK = {
    "cells": [dict(c, id=f"cel{i:02d}") for i, c in enumerate(CELULAS)],
    "metadata": {
        "colab": {"provenance": [], "name": "extrator_substantivos.ipynb"},
        "kernelspec": {"name": "python3", "display_name": "Python 3"},
        "language_info": {"name": "python"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

if __name__ == "__main__":
    DESTINO.parent.mkdir(exist_ok=True)
    DESTINO.write_text(json.dumps(NOTEBOOK, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Notebook gerado: {DESTINO.relative_to(RAIZ)}")
