"""Testes da lógica de extração.

O spaCy é substituído por um "modelo falso" (dicionário palavra -> classe),
o que mantém os testes rápidos e sem download de modelo. A integração real
com ``pt_core_news_*`` é validada no próprio Colab.
"""
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

import extrator_substantivos as ex

# ---------------------------------------------------------------- modelo falso
POS = {
    "casa": "NOUN", "casas": "NOUN", "gato": "NOUN", "informação": "NOUN",
    "saúde": "NOUN", "Brasil": "PROPN", "Aracaju": "PROPN", "a": "DET",
    "de": "ADP", "é": "AUX", "bonita": "ADJ", "x": "NOUN", "123": "NUM",
    "da": "ADP",
}
LEMAS = {"casas": "casa"}
STOP = {"a", "de", "é", "da"}


@dataclass
class FakeToken:
    text: str

    @property
    def pos_(self):
        return POS.get(self.text, "X")

    @property
    def lemma_(self):
        return LEMAS.get(self.text, self.text)

    @property
    def is_alpha(self):
        return self.text.isalpha()

    @property
    def is_stop(self):
        return self.text in STOP


class FakeNLP:
    def pipe(self, textos, batch_size=8):
        for t in textos:
            yield [FakeToken(w) for w in t.split()]


@pytest.fixture
def nlp():
    return FakeNLP()


def criar_pdf(caminho: Path, paginas: list[str]) -> Path:
    c = canvas.Canvas(str(caminho), pagesize=A4)
    for texto in paginas:
        y = 800
        for linha in texto.split("\n"):
            c.drawString(60, y, linha)
            y -= 18
        c.showPage()
    c.save()
    return caminho


# ---------------------------------------------------------------- limpar_texto
def test_limpar_texto_junta_hifenizacao_e_espacos():
    assert ex.limpar_texto("informa-\nção   da\n saúde") == "informação da saúde"


def test_limpar_texto_troca_ligaduras_e_remove_nulos():
    assert ex.limpar_texto("ﬁnal\x00 ﬂuxo") == "final fluxo"


# ------------------------------------------------------- extrair_substantivos
def test_filtra_apenas_substantivos(nlp):
    regs = ex.extrair_substantivos(["a casa de Aracaju é bonita"], nlp)
    assert [(r["termo"], r["classe"]) for r in regs] == [
        ("casa", "NOUN"),
        ("Aracaju", "PROPN"),
    ]


def test_ignora_numeros_e_termos_curtos(nlp):
    regs = ex.extrair_substantivos(["x 123 casa"], nlp, min_caracteres=2)
    assert [r["termo"] for r in regs] == ["casa"]


def test_somente_noun_quando_proprios_desligados(nlp):
    regs = ex.extrair_substantivos(["gato Brasil"], nlp, classes=("NOUN",))
    assert [r["termo"] for r in regs] == ["gato"]


def test_lema_aplica_so_em_substantivo_comum(nlp):
    regs = ex.extrair_substantivos(["casas Brasil"], nlp, usar_lema=True)
    assert [r["termo"] for r in regs] == ["casa", "Brasil"]


def test_minusculas_preserva_nome_proprio(nlp):
    regs = ex.extrair_substantivos(["Brasil"], nlp, minusculas=True)
    assert regs[0]["termo"] == "Brasil"


def test_registra_numero_da_pagina(nlp):
    regs = ex.extrair_substantivos(["gato", "casa"], nlp)
    assert [(r["termo"], r["pagina"]) for r in regs] == [("gato", 1), ("casa", 2)]


# ----------------------------------------------------------------- consolidar
def test_consolidar_conta_frequencia_e_paginas():
    regs = [
        {"pagina": 1, "termo": "casa", "classe": "NOUN"},
        {"pagina": 3, "termo": "casa", "classe": "NOUN"},
        {"pagina": 3, "termo": "casa", "classe": "NOUN"},
        {"pagina": 2, "termo": "gato", "classe": "NOUN"},
    ]
    df = ex.consolidar(regs, "a.pdf")
    assert list(df.columns) == ex.COLUNAS
    assert df.iloc[0].to_dict() == {
        "arquivo": "a.pdf", "termo": "casa", "classe": "NOUN",
        "frequencia": 3, "paginas": "1, 3",
    }
    assert df.iloc[1]["termo"] == "gato"


def test_consolidar_vazio_mantem_colunas():
    df = ex.consolidar([], "a.pdf")
    assert df.empty and list(df.columns) == ex.COLUNAS


# ------------------------------------------------------------------ PDF real
@pytest.mark.parametrize("motor", ex.MOTORES_PDF)
def test_extrair_texto_pdf_por_pagina(tmp_path, motor):
    pdf = criar_pdf(tmp_path / "t.pdf", ["gato casa", "Brasil"])
    paginas = ex.extrair_texto_pdf(pdf, motor=motor)
    assert len(paginas) == 2
    assert "gato" in paginas[0] and "Brasil" in paginas[1]


def test_motor_invalido(tmp_path):
    with pytest.raises(ValueError):
        ex.extrair_texto_pdf(tmp_path / "x.pdf", motor="foo")


def test_processar_pdf_ponta_a_ponta(tmp_path, nlp):
    pdf = criar_pdf(tmp_path / "doc.pdf", ["a casa de Aracaju", "casa gato"])
    df = ex.processar_pdf(pdf, nlp)
    freq = dict(zip(df["termo"], df["frequencia"]))
    assert freq == {"casa": 2, "Aracaju": 1, "gato": 1}
    assert set(df["arquivo"]) == {"doc.pdf"}


def test_pdf_sem_texto_levanta_erro(tmp_path, nlp):
    pdf = criar_pdf(tmp_path / "vazio.pdf", [""])
    with pytest.raises(ex.PDFSemTextoError):
        ex.processar_pdf(pdf, nlp)


# --------------------------------------------------------------------- pasta
def test_processar_pasta_isola_falhas(tmp_path, nlp):
    criar_pdf(tmp_path / "a.pdf", ["casa"])
    criar_pdf(tmp_path / "vazio.pdf", [""])
    (tmp_path / "quebrado.pdf").write_bytes(b"isto nao e um pdf")
    (tmp_path / "ignorar.txt").write_text("casa")

    df, falhas = ex.processar_pasta(tmp_path, nlp)
    assert set(df["arquivo"]) == {"a.pdf"}
    assert {nome for nome, _ in falhas} == {"vazio.pdf", "quebrado.pdf"}


def test_processar_pasta_arquivo_unico_e_inexistente(tmp_path, nlp):
    criar_pdf(tmp_path / "a.pdf", ["casa"])
    criar_pdf(tmp_path / "b.pdf", ["gato"])
    df, _ = ex.processar_pasta(tmp_path, nlp, arquivo="b.pdf")
    assert set(df["termo"]) == {"gato"}
    with pytest.raises(FileNotFoundError):
        ex.processar_pasta(tmp_path, nlp, arquivo="nao_existe.pdf")


def test_listar_pdfs_aceita_extensao_maiuscula(tmp_path):
    (tmp_path / "A.PDF").write_bytes(b"")
    (tmp_path / "b.txt").write_bytes(b"")
    assert [p.name for p in ex.listar_pdfs(tmp_path)] == ["A.PDF"]


# --------------------------------------------------------------------- saída
def df_exemplo():
    return pd.DataFrame(
        [
            ["a.pdf", "casa", "NOUN", 3, "1, 2"],
            ["b.pdf", "casa", "NOUN", 2, "1"],
            ["b.pdf", "saúde", "NOUN", 1, "4"],
        ],
        columns=ex.COLUNAS,
    )


def test_resumo_geral_soma_entre_arquivos():
    r = ex.resumo_geral(df_exemplo())
    assert r.iloc[0].to_dict() == {
        "termo": "casa", "classe": "NOUN", "frequencia": 5, "arquivos": 2,
    }


def test_salvar_csv_abre_com_acentos(tmp_path):
    criados = ex.salvar_resultados(df_exemplo(), tmp_path, "saida", "csv")
    assert {p.name for p in criados} == {"saida.csv", "saida_resumo.csv"}
    lido = pd.read_csv(tmp_path / "saida.csv", sep=";", encoding="utf-8-sig")
    assert "saúde" in set(lido["termo"])


def test_salvar_xlsx_tem_duas_abas(tmp_path):
    ex.salvar_resultados(df_exemplo(), tmp_path, "saida", "xlsx")
    abas = pd.read_excel(tmp_path / "saida.xlsx", sheet_name=None)
    assert set(abas) == {"substantivos", "resumo_geral"}


def test_salvar_formato_invalido(tmp_path):
    with pytest.raises(ValueError):
        ex.salvar_resultados(df_exemplo(), tmp_path, formato="pdf")
