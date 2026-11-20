# Guia do Google Colab

Passo a passo para quem vai **rodar** o notebook, sem precisar mexer em código.

## 1. Preparação única

1. **Conta Google do projeto.** Crie (ou use) uma conta Google compartilhada pela equipe.
   Dica: compartilhe a pasta do Drive com os integrantes em vez de compartilhar a senha.
2. No Google Drive, crie esta estrutura:

   ```
   Meu Drive/
   └── ExtratorSubstantivos/
       ├── entrada/   ← coloque os PDFs aqui
       └── saida/     ← os resultados são salvos aqui
   ```

   Se as pastas não existirem, o notebook as cria na primeira execução.
3. Abra o notebook: no GitHub, clique no botão **Open in Colab** do README, ou acesse
   <https://colab.research.google.com> → **GitHub** → cole a URL do repositório.

## 2. Rodando

1. Suba os PDFs na pasta `entrada`.
2. Na célula **3. Parâmetros**, ajuste os campos (são formulários, não precisa editar código):
   - `arquivo`: `todos` ou o nome exato de um PDF (`relatorio.pdf`).
   - `modelo`: `pt_core_news_sm` é rápido; `lg` é mais preciso e mais lento.
   - Marque/desmarque nomes próprios e forma de dicionário conforme a necessidade.
3. Menu **Ambiente de execução → Executar tudo** (atalho `Ctrl + F9`).
4. Na primeira execução o Colab pede **permissão de acesso ao Drive**: clique em
   *Conectar ao Google Drive* e autorize com a conta do projeto.
5. Ao final, abra `ExtratorSubstantivos/saida`:
   - `substantivos.csv` e `substantivos_resumo.csv` (separador `;`, abre direto no Excel pt-BR);
   - `substantivos.xlsx` com as abas `substantivos` e `resumo_geral`.

## 3. Rodando novamente em outro dia

O ambiente do Colab é descartado após algum tempo de inatividade, por isso a **primeira
célula reinstala as bibliotecas** a cada sessão. Basta repetir **Executar tudo**; leva
cerca de 1 a 2 minutos a mais na primeira vez do dia (instalação + download do modelo).

## 4. Problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| "Nenhum PDF encontrado em..." | PDFs na pasta errada | Mova para `ExtratorSubstantivos/entrada` |
| `[aviso] arquivo.pdf: sem texto selecionável` | PDF é imagem escaneada | Aplicar OCR antes (ex.: "Abrir com → Google Docs" ou Tesseract) |
| `FileNotFoundError: Arquivo não encontrado` | Nome em `arquivo` errado | Conferir nome exato, incluindo `.pdf` |
| Erro ao montar o Drive | Permissão negada | Reexecutar a célula 2 e autorizar com a conta certa |
| Palavras coladas/embaralhadas | PDF com colunas ou tabelas | Trocar `motor_pdf` para `pdfplumber` |
| Muitos termos estranhos | Modelo `sm` é menos preciso | Usar `pt_core_news_lg` e aumentar `min_caracteres` |
| `OSError` ao carregar o modelo | Download interrompido | Rodar novamente a célula 5 |

## 5. Salvando o notebook no GitHub (para a equipe)

No Colab: **Arquivo → Salvar uma cópia no GitHub**. Atenção: o notebook oficial é gerado
por `tools/build_notebook.py`; alterações de lógica devem ser feitas em
`src/extrator_substantivos.py` (veja `README.md`). Salvar diretamente do Colab é adequado
apenas para ajustes de texto/parâmetros padrão.
