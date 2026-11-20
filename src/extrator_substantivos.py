"""Extrator de substantivos em arquivos PDF (português do Brasil).

Fluxo:
    PDF --(pypdf | pdfplumber)--> texto por página
        --(spaCy, POS tagging)--> tokens com classe gramatical
        --(filtro NOUN / PROPN)--> termos
        --(pandas)--> tabela consolidada --> CSV / XLSX

O módulo não depende do Google Colab: o mesmo código roda no notebook e
localmente (veja a função ``main`` no final do arquivo).
"""
from __future__ import annotations

import importlib
import re
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

CLASSES_PADRAO = ("NOUN", "PROPN")
MOTORES_PDF = ("pypdf", "pdfplumber")
COLUNAS = ["arquivo", "termo", "classe", "frequencia", "paginas"]

_LIGATURAS = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl"}
_QUEBRA_COM_HIFEN = re.compile(r"(\w)-\s*\n\s*(\w)")


class PDFSemTextoError(Exception):
    """PDF sem camada de texto (provavelmente escaneado; exigiria OCR)."""


# --------------------------------------------------------------------------
# 1. Leitura do PDF
# --------------------------------------------------------------------------
def extrair_texto_pdf(caminho: str | Path, motor: str = "pypdf") -> list[str]:
    """Devolve uma lista com o texto bruto de cada página do PDF."""
    if motor not in MOTORES_PDF:
        raise ValueError(f"Motor inválido: {motor!r}. Use um de {MOTORES_PDF}.")

    caminho = str(caminho)
    if motor == "pypdf":
        from pypdf import PdfReader

        leitor = PdfReader(caminho)
        if leitor.is_encrypted:
            leitor.decrypt("")  # PDFs protegidos apenas contra edição
        return [(pagina.extract_text() or "") for pagina in leitor.pages]

    import pdfplumber

    with pdfplumber.open(caminho) as pdf:
        return [(pagina.extract_text() or "") for pagina in pdf.pages]


def limpar_texto(texto: str) -> str:
    """Normaliza o texto extraído do PDF antes da análise gramatical.

    - troca ligaduras tipográficas (ﬁ, ﬂ...) pelas letras comuns;
    - remove hífen opcional e junta palavras separadas por quebra de linha
      ("informa-\\nção" -> "informação");
    - colapsa espaços e quebras de linha.
    """
    for ligatura, letras in _LIGATURAS.items():
        texto = texto.replace(ligatura, letras)
    texto = texto.replace("\x00", " ").replace("\xad", "")
    texto = _QUEBRA_COM_HIFEN.sub(r"\1\2", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


# --------------------------------------------------------------------------
# 2. Análise gramatical (spaCy)
# --------------------------------------------------------------------------
def carregar_modelo(nome: str = "pt_core_news_sm"):
    """Carrega o modelo spaCy, baixando-o se ainda não estiver instalado.

    Parser e NER ficam desligados: só precisamos de POS tagging e lema.
    """
    import spacy

    desligar = ["parser", "ner"]
    try:
        return spacy.load(nome, exclude=desligar)
    except OSError:
        from spacy.cli import download

        download(nome)
        importlib.invalidate_caches()
        return spacy.load(nome, exclude=desligar)


def extrair_substantivos(
    paginas: Sequence[str],
    nlp: Any,
    classes: Iterable[str] = CLASSES_PADRAO,
    usar_lema: bool = False,
    minusculas: bool = True,
    min_caracteres: int = 2,
    ignorar_stopwords: bool = True,
) -> list[dict]:
    """Percorre as páginas e devolve um registro por substantivo encontrado.

    ``usar_lema`` e ``minusculas`` valem apenas para substantivos comuns
    (NOUN). Nomes próprios (PROPN) mantêm a grafia original, pois a inicial
    maiúscula faz parte da informação.
    """
    classes = set(classes)
    textos = [limpar_texto(p) for p in paginas]
    registros: list[dict] = []

    for numero, doc in enumerate(nlp.pipe(textos, batch_size=8), start=1):
        for token in doc:
            if token.pos_ not in classes or not token.is_alpha:
                continue
            if ignorar_stopwords and token.is_stop:
                continue

            termo = token.text
            if token.pos_ == "NOUN":
                if usar_lema and token.lemma_:
                    termo = token.lemma_
                if minusculas:
                    termo = termo.lower()

            if len(termo) < min_caracteres:
                continue
            registros.append({"pagina": numero, "termo": termo, "classe": token.pos_})

    return registros


def consolidar(registros: Sequence[dict], arquivo: str) -> pd.DataFrame:
    """Agrupa os registros por (termo, classe) com frequência e páginas."""
    agregado: dict[tuple[str, str], dict] = {}
    for r in registros:
        item = agregado.setdefault((r["termo"], r["classe"]), {"freq": 0, "pags": set()})
        item["freq"] += 1
        item["pags"].add(r["pagina"])

    linhas = [
        {
            "arquivo": arquivo,
            "termo": termo,
            "classe": classe,
            "frequencia": v["freq"],
            "paginas": ", ".join(str(p) for p in sorted(v["pags"])),
        }
        for (termo, classe), v in agregado.items()
    ]
    linhas.sort(key=lambda l: (-l["frequencia"], l["termo"].casefold()))
    return pd.DataFrame(linhas, columns=COLUNAS)


# --------------------------------------------------------------------------
# 3. Orquestração
# --------------------------------------------------------------------------
def processar_pdf(caminho: str | Path, nlp: Any, motor: str = "pypdf", **opcoes) -> pd.DataFrame:
    """Lê um PDF e devolve a tabela de substantivos dele."""
    caminho = Path(caminho)
    paginas = extrair_texto_pdf(caminho, motor=motor)
    if not any(p.strip() for p in paginas):
        raise PDFSemTextoError(
            "sem texto selecionável (PDF escaneado?). É necessário OCR antes."
        )
    registros = extrair_substantivos(paginas, nlp, **opcoes)
    return consolidar(registros, caminho.name)


def listar_pdfs(pasta: str | Path) -> list[Path]:
    """Lista os PDFs de uma pasta (sem recursão), em ordem alfabética."""
    return sorted(
        p for p in Path(pasta).iterdir() if p.is_file() and p.suffix.lower() == ".pdf"
    )


def processar_pasta(
    pasta_entrada: str | Path,
    nlp: Any,
    arquivo: str = "todos",
    motor: str = "pypdf",
    **opcoes,
) -> tuple[pd.DataFrame, list[tuple[str, str]]]:
    """Processa um PDF (``arquivo``) ou todos os PDFs da pasta.

    Devolve ``(tabela, falhas)``; ``falhas`` é uma lista de (arquivo, motivo).
    Um PDF problemático não interrompe os demais.
    """
    pasta_entrada = Path(pasta_entrada)
    if arquivo.strip().lower() in ("", "todos"):
        pdfs = listar_pdfs(pasta_entrada)
    else:
        alvo = pasta_entrada / arquivo
        if not alvo.is_file():
            raise FileNotFoundError(f"Arquivo não encontrado: {alvo}")
        pdfs = [alvo]

    tabelas: list[pd.DataFrame] = []
    falhas: list[tuple[str, str]] = []
    for pdf in pdfs:
        try:
            tabelas.append(processar_pdf(pdf, nlp, motor=motor, **opcoes))
        except PDFSemTextoError as erro:
            falhas.append((pdf.name, str(erro)))
        except Exception as erro:  # PDF corrompido, protegido por senha etc.
            falhas.append((pdf.name, f"{type(erro).__name__}: {erro}"))

    if not tabelas:
        return pd.DataFrame(columns=COLUNAS), falhas
    return pd.concat(tabelas, ignore_index=True), falhas


# --------------------------------------------------------------------------
# 4. Saída
# --------------------------------------------------------------------------
def resumo_geral(df: pd.DataFrame) -> pd.DataFrame:
    """Soma as frequências de cada termo em todos os PDFs processados."""
    if df.empty:
        return pd.DataFrame(columns=["termo", "classe", "frequencia", "arquivos"])
    resumo = df.groupby(["termo", "classe"], as_index=False).agg(
        frequencia=("frequencia", "sum"), arquivos=("arquivo", "nunique")
    )
    return resumo.sort_values(
        ["frequencia", "termo"], ascending=[False, True], kind="mergesort"
    ).reset_index(drop=True)


def salvar_resultados(
    df: pd.DataFrame,
    pasta_saida: str | Path,
    nome_base: str = "substantivos",
    formato: str = "csv",
) -> list[Path]:
    """Grava a tabela em CSV, XLSX ou ambos e devolve os caminhos criados.

    O CSV usa ``;`` e UTF-8 com BOM para abrir corretamente no Excel em
    português. O XLSX traz duas abas: ``substantivos`` e ``resumo_geral``.
    """
    if formato not in ("csv", "xlsx", "ambos"):
        raise ValueError("formato deve ser 'csv', 'xlsx' ou 'ambos'")

    pasta_saida = Path(pasta_saida)
    pasta_saida.mkdir(parents=True, exist_ok=True)
    resumo = resumo_geral(df)
    criados: list[Path] = []

    if formato in ("csv", "ambos"):
        destino = pasta_saida / f"{nome_base}.csv"
        df.to_csv(destino, sep=";", index=False, encoding="utf-8-sig")
        destino_resumo = pasta_saida / f"{nome_base}_resumo.csv"
        resumo.to_csv(destino_resumo, sep=";", index=False, encoding="utf-8-sig")
        criados += [destino, destino_resumo]

    if formato in ("xlsx", "ambos"):
        destino = pasta_saida / f"{nome_base}.xlsx"
        with pd.ExcelWriter(destino, engine="openpyxl") as escritor:
            df.to_excel(escritor, sheet_name="substantivos", index=False)
            resumo.to_excel(escritor, sheet_name="resumo_geral", index=False)
        criados.append(destino)

    return criados


# --- CLI ---  (esta seção NÃO é copiada para o notebook)
def main(argv: Sequence[str] | None = None) -> int:
    """Uso local: python src/extrator_substantivos.py data/entrada -o data/saida"""
    import argparse

    ap = argparse.ArgumentParser(description="Extrai substantivos de PDFs em português.")
    ap.add_argument("entrada", help="pasta com PDFs ou caminho de um PDF")
    ap.add_argument("-o", "--saida", default="data/saida", help="pasta de saída")
    ap.add_argument("--modelo", default="pt_core_news_sm")
    ap.add_argument("--motor", choices=MOTORES_PDF, default="pypdf")
    ap.add_argument("--formato", choices=("csv", "xlsx", "ambos"), default="csv")
    ap.add_argument("--lema", action="store_true", help="usar a forma de dicionário")
    ap.add_argument("--sem-proprios", action="store_true", help="ignorar nomes próprios")
    ap.add_argument("--min-caracteres", type=int, default=3)
    args = ap.parse_args(argv)

    entrada = Path(args.entrada)
    pasta, arquivo = (entrada.parent, entrada.name) if entrada.is_file() else (entrada, "todos")
    nlp = carregar_modelo(args.modelo)
    df, falhas = processar_pasta(
        pasta,
        nlp,
        arquivo=arquivo,
        motor=args.motor,
        classes=("NOUN",) if args.sem_proprios else CLASSES_PADRAO,
        usar_lema=args.lema,
        min_caracteres=args.min_caracteres,
    )
    for nome, motivo in falhas:
        print(f"[aviso] {nome}: {motivo}")
    if df.empty:
        print("Nenhum substantivo extraído.")
        return 1
    nome_base = Path(arquivo).stem if arquivo != "todos" else "substantivos"
    for caminho in salvar_resultados(df, args.saida, nome_base, args.formato):
        print(f"Gerado: {caminho}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
