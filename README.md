# Compilador JSS (Java Script Simplificado) — Front-end

Trabalho final de Compiladores (UFPI). Esta é a **versão final do front-end**:
implementa as três análises (**léxica**, **sintática** e **semântica**) da
linguagem JSS e é executado por linha de comando.

## 1. Pré-requisitos / Instalação

- **Python 3** (3.8 ou superior). É só isso.
- **Nenhuma biblioteca externa** — léxico, sintático e semântico foram escritos
  à mão, usando apenas a biblioteca padrão do Python.

```bash
python3 --version
```

## 2. Como executar

```bash
# Lendo de um arquivo:
python3 jssc.py exemplos/ok1_fatorial.jss

# Lendo da entrada padrão (stdin), como pede a especificação (item 3.1c):
python3 jssc.py < exemplos/ok1_fatorial.jss
```

Saída: `Compilacao concluida com sucesso.` para programas válidos, ou
`Erro lexico/sintatico/semantico na linha N: ...` quando há um problema.

### Opções extras (para inspecionar as etapas)

```bash
python3 jssc.py exemplos/ok1_fatorial.jss --tokens   # tokens (analisador léxico)
python3 jssc.py exemplos/ok1_fatorial.jss --ast      # árvore (analisador sintático)
```

## 3. Exemplos incluídos

| Arquivo | O que demonstra | Resultado |
|---|---|---|
| `exemplos/ok1_fatorial.jss` | Função recursiva, `if/else`, chamadas | sucesso |
| `exemplos/ok2_vetores.jss` | Vetores, `for`, `while`, operadores, conversão | sucesso |
| `exemplos/ok3_for_multiplo.jss` | `for` com várias atribuições | sucesso |
| `exemplos/ok4_classes.jss` | Classe, construtor, métodos, `this`, `new` | sucesso |
| `tests/basics.jss` | Tipos, constantes, vetores 1D e 2D (matriz) | sucesso |
| `tests/control_flow.jss` | `if/else`, `for`/`while` aninhados, `break` | sucesso |
| `tests/operators.jss` | Todos os operadores da Tabela 1 | sucesso |
| `exemplos/erro_lexico.jss` | Caractere inválido (`@`) | erro léxico, linha 5 |
| `exemplos/erro_sintatico.jss` | Parêntese não fechado | erro sintático, linha 4 |
| `exemplos/erro_semantico.jss` | Variável não declarada | erro semântico, linha 5 |
| `exemplos/erro_tipo.jss` | Atribuição de tipo incompatível | erro semântico, linha 5 |

## 4. Estrutura do projeto

```
jssc.py          # Linha de comando: junta as três análises
lexer.py         # Análise léxica:   texto   -> tokens
jss_parser.py    # Análise sintática: tokens  -> árvore sintática (AST)
semantic.py      # Análise semântica: percorre a AST verificando as regras
exemplos/        # Programas .jss de exemplo (válidos e com erro)
tests/           # Códigos de teste compartilhados pelo monitor
```

## 5. O que o front-end cobre

- **Léxico:** palavras reservadas, tipos, identificadores, inteiros e reais
  (com expoente), strings com escapes, comentários `//`, todos os operadores.
- **Sintático:** variáveis/constantes, vetores (inclusive **multidimensionais**),
  **classes/objetos** (atributos, `constructor`, métodos, `this`, `new`),
  funções (com `void` e recursão), `if/else if/else`, `while`, `for`, `return`,
  `break`, funções nativas (`console.log`, `input`) e conversões de tipo, com
  toda a precedência da Tabela 1.
- **Semântico:** escopos (global e de bloco), declaração antes do uso, proibição
  de redeclaração no mesmo escopo, tipagem forte das expressões com conversões
  implícitas, constantes imutáveis, chamadas com aridade/tipos corretos,
  `return` compatível com o tipo da função e `break` apenas dentro de laços.
