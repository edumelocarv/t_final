# Compilador JSS (Java Script Simplificado)

Trabalho final de Compiladores (UFPI). Compilador **completo** da linguagem JSS:

- **Front-end (análise):** léxica, sintática e semântica — em Python puro.
- **Back-end (síntese):** gera código intermediário **JASMIN** (assembly da JVM),
  monta um `.class` e o executa. O mapeamento JSS → JVM é quase 1:1
  (classe JSS → classe da JVM, `str` → `String`, vetor → array).

## 1. Pré-requisitos / Instalação

Para o **front-end** (análise):
- **Python 3** (3.8 ou superior). Nenhuma biblioteca externa.

Para o **back-end** (gerar e executar):
- **Java (JDK 8+)** — usado para montar com o Jasmin e executar o `.class`.
- **Jasmin 2.4** — já incluído no projeto em `tools/jasmin.jar`
  (caso precise baixar: https://sourceforge.net/projects/jasmin/).

```bash
python3 --version
java -version
```

## 2. Como executar

### Só a análise (front-end)
```bash
python3 jssc.py exemplos/ok1_fatorial.jss      # de um arquivo
python3 jssc.py < exemplos/ok1_fatorial.jss    # da entrada padrão (item 3.1c)
```
Saída: `Compilacao concluida com sucesso.` ou
`Erro lexico/sintatico/semantico na linha N: ...`.

### Compilar e executar (back-end)
```bash
python3 jssc.py exemplos/ok1_fatorial.jss --jvm   # gera build/Programa.class
python3 jssc.py exemplos/ok1_fatorial.jss --run   # gera E executa o programa
```
Para programas que usam `input`, forneça a entrada pelo terminal, por exemplo:
```bash
echo 5 | python3 jssc.py exemplos/ok1_fatorial.jss --run
```

### Opções extras (para inspecionar as etapas)
```bash
python3 jssc.py programa.jss --tokens   # tokens (analisador léxico)
python3 jssc.py programa.jss --ast      # árvore sintática (analisador sintático)
```

## 3. Exemplos incluídos

Programas válidos (compilam e executam com `--run`):

| Arquivo | Demonstra | Entrada |
|---|---|---|
| `exemplos/ok1_fatorial.jss` | Recursão, `if/else`, `input` | um inteiro |
| `exemplos/ok2_vetores.jss` | Vetores, `for`/`while`, conversão | — |
| `exemplos/ok3_for_multiplo.jss` | `for` com várias atribuições | — |
| `exemplos/ok4_classes.jss` | Classe, `constructor`, métodos, `this`, `new` | — |
| `testes/1_basics.jss` | Tipos, constantes, vetores 1D e matriz 2D | — |
| `testes/2_operators.jss` | Todos os operadores da Tabela 1 | — |
| `testes/3_control_flow.jss` | `if/else`, `for`/`while` aninhados, `break` | — |
| `testes/4_strings_casts.jss` | Strings, concatenação, casts, `input` | 3 ints + 2 palavras |
| `testes/5_classes.jss` | Classes com atributos, métodos e matriz | — |

Programas com erro (o compilador para e aponta a linha):

| Arquivo | Erro |
|---|---|
| `exemplos/erro_lexico.jss` | léxico (caractere `@`), linha 5 |
| `exemplos/erro_sintatico.jss` | sintático (parêntese), linha 4 |
| `exemplos/erro_semantico.jss` | semântico (variável não declarada), linha 5 |
| `exemplos/erro_tipo.jss` | semântico (tipo incompatível), linha 5 |

Bateria de conformidade (61 casos derivados da especificação):
```bash
python3 tests/conformance.py
```

## 4. Estrutura do projeto

```
jssc.py          # Linha de comando: encadeia front-end e back-end
lexer.py         # Análise léxica:    texto   -> tokens
jss_parser.py    # Análise sintática: tokens  -> árvore sintática (AST)
semantic.py      # Análise semântica: verifica a AST (tipos, escopos, ...)
codegen.py       # Back-end:          AST     -> JASMIN (bytecode da JVM)
tools/jasmin.jar # Montador Jasmin (AST em JASMIN -> .class)
build/           # Saída gerada (.j e .class)  [criada automaticamente]
exemplos/ testes/  Programas .jss de exemplo e testes
tests/conformance.py  Bateria de conformidade do front-end
```

## 5. O que o compilador cobre

- **Léxico:** palavras reservadas, tipos, identificadores, inteiros e reais
  (com expoente), strings com escapes, comentários `//`, todos os operadores.
- **Sintático:** variáveis/constantes, vetores (inclusive **multidimensionais**),
  **classes/objetos**, funções (com `void` e recursão), `if/else if/else`,
  `while`, `for`, `return`, `break`, funções nativas (`console.log`, `input`) e
  conversões de tipo, com toda a precedência da Tabela 1.
- **Semântico:** escopos (global e de bloco), declaração antes do uso, anti-
  redeclaração, tipagem forte com conversões implícitas, constantes imutáveis,
  chamadas com aridade/tipos corretos, `return` compatível (retorno não pode ser
  vetor, mas pode ser objeto — conforme a v3 da especificação) e `break` apenas
  em laços.
- **Back-end (JASMIN):** primitivos (`int`, `real`, `str`, `bool`), operadores
  com curto-circuito, vetores e matrizes, classes/objetos, funções e recursão,
  `console.log`, `input` e conversões — gerando um executável da JVM.
