# Arquitetura e decisões técnicas

## Visão geral

```
PDF(s) no Drive
   │  extrair_texto_pdf()        pypdf | pdfplumber → lista de textos por página
   ▼
limpar_texto()                   ligaduras, hifenização, espaços
   │
   ▼  extrair_substantivos()     spaCy nlp.pipe → token.pos_ ∈ {NOUN, PROPN}
registros [{pagina, termo, classe}]
   │  consolidar()               pandas: frequência e páginas por (termo, classe)
   ▼
DataFrame [arquivo, termo, classe, frequencia, paginas]
   │  salvar_resultados()        CSV (;) / XLSX (2 abas)
   ▼
Drive/saida
```

Orquestração: `processar_pdf` (um arquivo) e `processar_pasta` (vários, isolando falhas).

## Decisões

| Decisão | Motivo |
|---|---|
| **Um único módulo (`src/`) e notebook gerado** | Evita duplicar código entre notebook e testes; o que é testado é exatamente o que roda no Colab. |
| **`pypdf` como padrão, `pdfplumber` opcional** | `pypdf` é leve e rápido; `pdfplumber` lida melhor com colunas/tabelas. O usuário escolhe pelo formulário. |
| **Texto processado por página** | Permite registrar em quais páginas cada termo aparece e evita estourar o limite de tamanho de texto do spaCy. |
| **Parser e NER desligados** | Só é preciso POS tagging e lema; fica mais rápido e usa menos memória. |
| **Lema e minúsculas só para `NOUN`** | Nomes próprios perdem informação se forem minusculizados; mantêm a grafia original. |
| **`is_alpha` + `min_caracteres` + stopwords** | Remove números, pontuação, siglas de uma letra e ruído comum do *tagger*. |
| **CSV com `;` e UTF-8 BOM** | Abre corretamente (acentos e colunas) no Excel configurado em português. |
| **Falha de um PDF não interrompe os demais** | PDFs escaneados, corrompidos ou protegidos são listados como aviso ao final. |
| **Modelo carregado com auto-download** | O usuário só escolhe o nome no formulário; `carregar_modelo` baixa se faltar. |
| **Modelo simulado nos testes** | Testes rápidos e determinísticos, sem baixar centenas de MB. |

## Contrato das funções principais

| Função | Entrada | Saída |
|---|---|---|
| `extrair_texto_pdf(caminho, motor)` | caminho do PDF | `list[str]`, um item por página |
| `limpar_texto(texto)` | texto bruto | texto normalizado |
| `carregar_modelo(nome)` | nome do modelo spaCy | objeto `nlp` |
| `extrair_substantivos(paginas, nlp, ...)` | textos + `nlp` | `list[dict]` com `pagina`, `termo`, `classe` |
| `consolidar(registros, arquivo)` | registros | `DataFrame` (colunas em `COLUNAS`) |
| `processar_pdf(caminho, nlp, ...)` | PDF | `DataFrame`; levanta `PDFSemTextoError` |
| `processar_pasta(pasta, nlp, arquivo, ...)` | pasta | `(DataFrame, falhas)` |
| `resumo_geral(df)` | tabela | soma por termo entre arquivos |
| `salvar_resultados(df, pasta, nome, formato)` | tabela | lista de caminhos criados |

## Limitações e evoluções possíveis

- **OCR** para PDFs escaneados (Tesseract / `ocrmypdf`) como etapa opcional antes da leitura.
- **Lista de exclusão** personalizada (termos irrelevantes: "página", "figura", cabeçalhos repetidos).
- **Remoção de cabeçalho/rodapé** repetido em todas as páginas.
- **Nuvem de palavras / gráfico** dos termos mais frequentes na célula de prévia.
- **Extração de outras classes** (verbos, adjetivos): bastaria passar `classes=("VERB",)`;
  a função já aceita qualquer etiqueta POS do spaCy (Universal Dependencies).
- **Cache do modelo no Drive** para acelerar a primeira célula de cada sessão.

## Testes

`pytest` cobre: limpeza de texto, filtros de classe, lematização, consolidação, leitura de PDF
real com os dois motores (PDFs gerados com `reportlab`), PDF sem texto/corrompido, processamento
de pasta e exportação CSV/XLSX. A integração com os modelos reais do spaCy é validada rodando o
notebook no Colab com um PDF de exemplo.
