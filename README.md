# Compilador JSS (Java Script Simplificado) — Front-end

Trabalho final de Compiladores (UFPI). Esta entrega é a **prévia do front-end**:
contém o **analisador léxico** e o **analisador sintático** da linguagem JSS,
executáveis por linha de comando.

## 1. Pré-requisitos / Instalação

- **Python 3** (versão 3.8 ou superior). É só isso.
- **Nenhuma biblioteca externa** precisa ser instalada — o léxico e o sintático
  foram escritos à mão, usando apenas a biblioteca padrão do Python.

Verifique sua instalação:

```bash
python3 --version
```

## 2. Como executar

O compilador lê um programa `.jss` e diz se ele é válido ou aponta o erro
(com a linha onde ocorreu).

```bash
# Lendo de um arquivo:
python3 jssc.py exemplos/ok1_fatorial.jss

# Lendo da entrada padrão (stdin):
python3 jssc.py < exemplos/ok1_fatorial.jss
```

### Opções extras (para inspecionar as etapas)

```bash
# Mostra a lista de TOKENS gerada pelo analisador léxico:
python3 jssc.py exemplos/ok1_fatorial.jss --tokens

# Mostra a ÁRVORE SINTÁTICA gerada pelo analisador sintático:
python3 jssc.py exemplos/ok1_fatorial.jss --ast
```

## 3. Exemplos incluídos

| Arquivo | O que demonstra | Resultado esperado |
|---|---|---|
| `exemplos/ok1_fatorial.jss` | Função recursiva, `if/else`, chamadas | sucesso |
| `exemplos/ok2_vetores.jss` | Vetores, `for`, `while`, operadores, conversão | sucesso |
| `exemplos/ok3_for_multiplo.jss` | `for` com várias atribuições (init e update) | sucesso |
| `exemplos/erro_lexico.jss` | Caractere inválido (`@`) | erro léxico na linha 5 |
| `exemplos/erro_sintatico.jss` | Parêntese não fechado | erro sintático na linha 4 |

Exemplos de saída:

```
$ python3 jssc.py exemplos/ok1_fatorial.jss
Compilacao concluida com sucesso.

$ python3 jssc.py exemplos/erro_lexico.jss
Erro lexico na linha 5: caractere invalido '@'

$ python3 jssc.py exemplos/erro_sintatico.jss
Erro sintatico na linha 4: esperava ')' para fechar os parenteses, mas encontrei ';'
```

## 4. Estrutura do projeto

```
jssc.py          # Programa de linha de comando (junta tudo)
lexer.py         # Analisador léxico: texto  -> tokens
jss_parser.py    # Analisador sintático: tokens -> árvore sintática
exemplos/        # Programas .jss de teste (válidos e com erro)
```

## 5. Estado da implementação

Cobertos nesta prévia:

- **Léxico (completo):** palavras reservadas, tipos, identificadores, números
  inteiros e reais (com expoente), strings com escapes, comentários `//`,
  todos os operadores e a pontuação.
- **Sintático:** declaração de variáveis/constantes (incl. vetores), funções,
  comandos `if/else if/else`, `while`, `for` (com listas de atribuições/
  declarações separadas por vírgula, conforme a especificação), `return`,
  `break`, chamadas de função e funções nativas (`console.log`, `input`),
  conversões de tipo (`int(...)`, `real(...)`, ...) e expressões com toda a
  tabela de precedência.

Próxima etapa (versão final do front-end, 25/jun):

- Declaração de **classes e objetos**.
- **Análise semântica** (tipos, escopos, declaração antes do uso, etc.).

## 6. Extensões desta branch (`feat/testes-monitor`)

Esta branch habilita dois recursos usados nos testes de `tests/` que vão **além
do que a especificação escreve** (a branch `main` segue a spec à risca):

- **Vetores multidimensionais (matrizes):** `let int[3][3] matriz;` e
  `matriz[i][j]`. A spec define apenas vetores de uma dimensão.
- **Atribuição composta lógica:** `&&=` e `||=` (a spec exemplifica apenas as
  aritméticas `+=`, `-=`, ...).

Com isso, os três arquivos de `tests/` compilam com sucesso.
