# Guia de Apresentação (orientado ao código) — Front-end do Compilador JSS

Esta apresentação é conduzida **abrindo o código**. Para cada fase você abre o
arquivo, aponta as classes/métodos/linhas e explica o que fazem. Os comandos de
terminal servem para mostrar a **saída** daquele código.

Marcadores:
- 📂 **Abra** = abra este arquivo no editor.
- 👉 **Aponte** = mostre esta classe/método/linha.
- 🗣️ **Diga** = o que falar.
- 💻 **Rode** = comando no terminal (mostra a saída do código).

> Antes de começar: terminal aberto na pasta do projeto e o editor com os 4
> arquivos (`lexer.py`, `jss_parser.py`, `semantic.py`, `jssc.py`).

---

## PARTE 0 — Visão geral (30s)

🗣️ Diga:
> "O front-end tem três análises, e cada uma é um arquivo: a **léxica**
> (`lexer.py`), a **sintática** (`jss_parser.py`) e a **semântica**
> (`semantic.py`). O `jssc.py` é a linha de comando que encadeia as três. A
> estrutura central que liga tudo é a **árvore sintática (AST)**: o léxico produz
> tokens, o sintático monta a AST a partir deles, e a semântica percorre essa AST.
> O fluxo é: texto → tokens → AST → AST verificada. A linguagem é estilo script:
> a função `main` é facultativa e pode haver comandos no nível do arquivo."

---

## PARTE 1 — Análise Léxica · 📂 `lexer.py`

🗣️ Diga: "O léxico transforma o texto numa lista de tokens. Um token é a menor
unidade com significado."

👉 Aponte **a classe `Token`** ([lexer.py:36](lexer.py:36)):
> "Cada token guarda três coisas: `tipo` (a categoria), `valor` (o texto) e
> `linha`. É essa `linha` que vai permitir apontar onde ocorrem os erros."

👉 Aponte **a função `tokenizar`** ([lexer.py:58](lexer.py:58)) — o coração do léxico:
> "Tem um laço `while` que olha um caractere por vez e decide o que começa ali."
Percorra os ramos do laço, apontando cada `if`:
- quebra de linha → incrementa `linha`;
- espaço → ignora;
- `//` → consome até o fim da linha (comentário);
- `"` → chama `_ler_string`;
- dígito → chama `_ler_numero`;
- letra ou `_` → lê a palavra e chama `_classificar_palavra`;
- senão → `_casar_operador`;
- se nada casar → lança `ErroLexico` ([lexer.py:48](lexer.py:48)) com a linha.

👉 Aponte os auxiliares e diga em uma frase cada:
- `_classificar_palavra` ([lexer.py:124](lexer.py:124)) — decide se a palavra é
  reservada, tipo, booleano, `null` ou identificador.
- `_ler_string` ([lexer.py:137](lexer.py:137)) — lê `"..."` tratando escapes (`\n`).
- `_ler_numero` ([lexer.py:162](lexer.py:162)) — lê o número e diz se é `INT` ou
  `REAL` (trata expoente como `10.8E2`).
- `_casar_operador` ([lexer.py:194](lexer.py:194)) — reconhece o operador casando o
  mais longo primeiro (por isso a lista `OPERADORES` no topo vai de `**=`/`==` antes
  de `*`/`=`).

💻 Rode (mostra a saída deste arquivo):
```bash
python3 jssc.py exemplos/ok1_fatorial.jss --tokens
```
🗣️ "Cada linha aqui é um `Token` produzido pela `tokenizar`, com a categoria e a linha."

---

## PARTE 2 — Análise Sintática e a AST · 📂 `jss_parser.py`

Esta é a parte central. Comece pela estrutura da árvore.

### 2.1 A estrutura da árvore: a classe `No`
👉 Aponte **a classe `No`** ([jss_parser.py:13](jss_parser.py:13)):
> "A AST é uma árvore de objetos `No`. Cada nó tem quatro campos: `tipo` (o
> rótulo, ex.: `OpBin`), `valor` (nas folhas, ex.: `+` ou `x`), `linha`, e
> `filhos` (a lista de nós abaixo dele). Toda a árvore é feita desses objetos."

### 2.2 Como o parser monta a árvore
🗣️ Diga:
> "Uso **descida recursiva**: cada regra da gramática é um método `parse_*`, e
> **cada um devolve um `No`**. Quando uma regra usa outra, o `No` devolvido vira
> **filho**. Por isso a árvore espelha as chamadas."

👉 Aponte a navegação ([jss_parser.py:35](jss_parser.py:35)–69): `atual`, `avancar`,
`checar_valor`, `checar_tipo`, `consumir_valor`/`consumir_tipo` (exigem um token ou
lançam `ErroSintatico`).
> "Detalhe: `checar_valor` ([jss_parser.py:44](jss_parser.py:44)) só casa
> operadores e palavras-chave — nunca um literal. É o que evita confundir a string
> `\"!\"` com o operador `!`."

👉 Aponte o topo da gramática:
- `parse_programa` ([jss_parser.py:74](jss_parser.py:74)) — devolve
  `No("Programa", ...)`. Aceita **declarações** (`function`, `class`) e também
  **comandos soltos** (estilo script), pois a `main` é facultativa.
- `parse_comando` ([jss_parser.py:220](jss_parser.py:220)) — despacha cada tipo de
  comando (declaração de variável, `if`, `while`, `for`, `return`, `break`, bloco
  ou expressão).

### 2.3 A precedência sai da estrutura (o exemplo-chave)
👉 Aponte a **cadeia de expressões** — uma função por nível, da mais baixa à mais alta:
`parse_atribuicao` ([:313](jss_parser.py:313)) → `parse_ou` ([:321](jss_parser.py:321))
→ `parse_e` ([:328](jss_parser.py:328)) → `parse_comparacao` ([:335](jss_parser.py:335))
→ `parse_aditivo` ([:342](jss_parser.py:342)) → `parse_multiplicativo` ([:349](jss_parser.py:349))
→ `parse_exponenciacao` ([:356](jss_parser.py:356)) → `parse_unario` ([:363](jss_parser.py:363))
→ `parse_posfixo` ([:369](jss_parser.py:369)) → `parse_primario` ([:402](jss_parser.py:402)).

🗣️ Diga:
> "Como `parse_aditivo` chama `parse_multiplicativo` para montar cada lado, quem
> tem precedência maior fica **mais fundo** na árvore — e é avaliado primeiro.
> Veja com `2 + 3 * 4`:"

💻 Rode:
```bash
printf 'let int x = 2 + 3 * 4;' | python3 jssc.py --ast
```
Saída (aponte que o `*` ficou abaixo do `+`):
```
            OpBin (+)
            |- Int (2)
            `- OpBin (*)
               |- Int (3)
               `- Int (4)
```

👉 Aponte `parse_primario` ([jss_parser.py:402](jss_parser.py:402)):
> "É a base da recursão: cria as folhas e os casos básicos — números, strings,
> identificadores, `(expr)`, conversões `int(...)`, `new`, literal de vetor e
> `this`."
E `parse_posfixo` ([:369](jss_parser.py:369)): trata `f()` (chamada), `v[i]`
(índice) e `obj.x` (membro).

### 2.4 As outras regras (aponte rapidamente)
- `parse_funcao` ([:87](jss_parser.py:87)) e `parse_tipo_com_dims`
  ([:120](jss_parser.py:120)) — tipos com dimensão, inclusive em parâmetros e
  **retorno** (`int[5]`); `parse_var_decl` ([:154](jss_parser.py:154)) (vetores e
  matrizes pelo laço de dimensões); `parse_bloco` ([:146](jss_parser.py:146)).
- `parse_classe` ([:184](jss_parser.py:184)) e `parse_membro_classe`
  ([:194](jss_parser.py:194)) — decide se o membro é atributo, `constructor` ou
  método (o método pode ser `void`).
- `parse_if` ([:241](jss_parser.py:241)), `parse_while` ([:262](jss_parser.py:262)),
  `parse_for` ([:269](jss_parser.py:269)), `parse_return` ([:299](jss_parser.py:299)).

### 2.5 Como a AST alimenta as próximas fases
🗣️ Diga:
> "Essa árvore é a estrutura central: a análise semântica percorre ela, e na
> próxima etapa o back-end vai percorrer a **mesma** árvore para gerar código.
> Por isso cada nó guarda a `linha` e tem um rótulo claro."
👉 Aponte `imprimir_arvore` ([jss_parser.py:463](jss_parser.py:463)) — é só uma
ferramenta de visualização da AST (o modo `--ast`).

💻 Rode (a árvore de um programa real):
```bash
python3 jssc.py exemplos/ok4_classes.jss --ast
```

---

## PARTE 3 — Análise Semântica · 📂 `semantic.py`

🗣️ Diga: "A semântica **percorre a AST** verificando o significado — tipos,
escopos e as regras da linguagem."

👉 Aponte **`Analisador.analisar`** ([semantic.py:43](semantic.py:43)):
> "Trabalha em duas passagens: primeiro `coletar` registra todas as funções,
> classes e variáveis globais — é o que permite recursão e usar algo antes da
> declaração; depois percorre os corpos e os comandos soltos do topo."

👉 Aponte as duas estruturas no `__init__` ([semantic.py:33](semantic.py:33)):
- `self.escopos` — uma **pilha de escopos** (dicionários nome→tipo).
- `self.funcoes` e `self.classes` — as tabelas de símbolos globais.

👉 Aponte a **passagem 1**: `coletar` ([:111](semantic.py:111)),
`registrar_funcao`/`registrar_global`/`registrar_classe`
([:137](semantic.py:137), [:147](semantic.py:147), [:159](semantic.py:159)).

👉 Aponte o **controle de escopo**: `declarar` ([:98](semantic.py:98)) barra
redeclaração no mesmo escopo; `buscar` ([:103](semantic.py:103)) procura do escopo
interno até o global (declaração antes do uso).

👉 Aponte o **coração da tipagem**: `tipo_de` ([semantic.py:363](semantic.py:363)):
> "Recebe um nó da AST, olha o `no.tipo` e devolve o tipo da expressão, descendo
> nos filhos. Daqui saem os métodos por construção: `tipo_opbin`
> ([:435](semantic.py:435)) aplica as regras da Tabela 1, `tipo_atrib`
> ([:470](semantic.py:470)) checa atribuições e constantes (`lvalue_const` em
> [:498](semantic.py:498)), `tipo_chamada` ([:553](semantic.py:553)) confere os
> argumentos, etc."

👉 Aponte as checagens de comandos: `analisar_return` ([:339](semantic.py:339)),
`analisar_break` ([:352](semantic.py:352)), e `analisar_subrotina`
([:214](semantic.py:214)) que exige `return` em função não-`void` (via
`tem_return_com_valor` em [:228](semantic.py:228)).

💻 Rode (mostra as regras pegando os erros, com a linha):
```bash
python3 jssc.py exemplos/erro_semantico.jss     # variável não declarada
python3 jssc.py exemplos/erro_tipo.jss          # tipo incompatível
echo 'const int N=1; N=2;' | python3 jssc.py    # const imutável
echo 'break;'             | python3 jssc.py     # break fora de laço
```

---

## PARTE 4 — Linha de comando · 📂 `jssc.py`

👉 Aponte **`main`** ([jssc.py:35](jssc.py:35)):
> "Aqui se vê o front-end inteiro encadeado: `tokenizar` → `Parser().parse_programa`
> → `Analisador().analisar`. E os três `except` no fim capturam `ErroLexico`,
> `ErroSintatico` e `ErroSemantico`, imprimindo a mensagem com a linha."
👉 `ler_codigo` ([jssc.py:24](jssc.py:24)) — lê de um arquivo ou da entrada padrão
(item 3.1.c).

💻 Rode (sucesso e os dois primeiros erros):
```bash
python3 jssc.py exemplos/ok1_fatorial.jss
python3 jssc.py exemplos/erro_lexico.jss
python3 jssc.py exemplos/erro_sintatico.jss
```

---

## PARTE 5 — Verificação

🗣️ Diga: "Para provar que está de acordo com a especificação, tenho uma bateria de
casos derivados do spec — válidos que devem compilar e errados que devem ser
recusados na fase certa."

💻 Rode a bateria de conformidade:
```bash
python3 tests/conformance.py
```
→ `TOTAL: 59 casos, 0 falha(s)`.

🗣️ Diga: "E também rodo os arquivos de teste que o senhor enviou."
💻 Rode os testes do professor:
```bash
for f in testes/*.jss; do echo "== $f =="; python3 jssc.py "$f"; done
```
→ `1` a `6` compilam com sucesso; `7` e `8` são arquivos de erro e falham,
apontando a linha.

---

## PARTE 6 — Encerramento

🗣️ Diga:
> "Então: três análises, cada uma num arquivo; a AST como estrutura central, que a
> semântica percorre e que o back-end vai reaproveitar; execução por linha de
> comando reportando os erros das três fases com a linha; e duas baterias de
> testes (a minha e a do senhor) comprovando a conformidade. O próximo passo é o
> back-end, traduzindo essa árvore para código intermediário."

---

## Checklist antes de apresentar
- [ ] Editor aberto com os 4 arquivos; terminal na pasta do projeto.
- [ ] Rodei `--tokens` e `--ast` em um exemplo (Partes 1 e 2).
- [ ] Rodei os `erro_*`, `tests/conformance.py` e os `testes/` do professor.
- [ ] Reli as Partes 1 e 2 (são as que o professor mais aprofunda).
