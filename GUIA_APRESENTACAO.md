# Guia de Apresentação — Front-end COMPLETO do Compilador JSS

Este é o seu roteiro para a apresentação final do front-end. A ideia é
**apresentar de forma proativa**: você conduz, percorrendo a especificação e
mostrando que cada item está implementado, de modo que o professor não precise
perguntar nada ao final.

Use os marcadores:
- 🗣️ **Diga** = o que falar.
- 💻 **Mostre** = o comando para rodar no terminal.

> Antes de começar: abra o terminal na pasta do projeto e teste
> `python3 jssc.py exemplos/ok1_fatorial.jss` uma vez.

---

## PARTE 0 — Abertura (uns 30 segundos)

🗣️ Diga:
> "Eu desenvolvi o front-end completo de um compilador para a linguagem JSS, em
> Python, sem bibliotecas externas. Ele faz as três análises — **léxica**,
> **sintática** e **semântica** — e roda por linha de comando: lê um programa
> `.jss` e responde com sucesso, ou com um erro indicando a linha. Vou mostrar
> rodando e depois percorrer cada item da especificação."

🗣️ Conceitos em uma frase (caso precise):
- **Análise léxica:** quebra o texto em *tokens* (as "palavras" da linguagem).
- **Análise sintática:** verifica se os tokens formam frases válidas (a gramática)
  e monta a **árvore sintática**.
- **Análise semântica:** verifica o *significado* — tipos, escopos, se a variável
  foi declarada, etc.

---

## PARTE 1 — Execução por linha de comando (item 3.1.c)

🗣️ Diga:
> "Como a especificação pede, o compilador lê da entrada padrão ou de um arquivo
> e escreve na saída padrão."

💻 Mostre (programa válido):
```bash
python3 jssc.py exemplos/ok1_fatorial.jss
python3 jssc.py < exemplos/ok1_fatorial.jss
```
→ `Compilacao concluida com sucesso.`

💻 Mostre as etapas internas (opcional, mas impressiona):
```bash
python3 jssc.py exemplos/ok1_fatorial.jss --tokens   # saída do analisador léxico
python3 jssc.py exemplos/ok1_fatorial.jss --ast      # saída do analisador sintático
```
🗣️ Diga, apontando a árvore:
> "Essa é a árvore sintática. Repare que a multiplicação ficou acima da chamada
> recursiva, respeitando a precedência. Essa árvore é o que alimenta o back-end
> na próxima etapa."

---

## PARTE 2 — Percorrendo a especificação (item a + b)

Aqui você "varre" a especificação. Para cada ponto: fale e, quando útil, mostre.

### 2.1 Identificadores, variáveis, constantes e escopo (seção 4.1)
🗣️ Diga:
> "Identificadores começam com letra ou underscore e o léxico já barra qualquer
> caractere inválido. `let` e `const` têm **escopo de bloco** e variáveis fora de
> funções são **globais**. A semântica verifica três coisas: não pode redeclarar
> o mesmo nome no mesmo escopo, não pode usar antes de declarar, e **constante
> não pode ser reatribuída**."

💻 Mostre (cada um aponta a linha do erro):
```bash
echo 'function void main(){ let int x=1; let int x=2; }' | python3 jssc.py   # redeclaração
echo 'function void main(){ const int N=1; N=2; }'       | python3 jssc.py   # const imutável
```

### 2.2 Tipos primitivos (seção 4.2.1)
🗣️ Diga:
> "Os quatro primitivos estão implementados: `int`, `real`, `str` e `bool`, com a
> tipagem forte da linguagem. O léxico reconhece inteiros, reais com expoente
> como `10.8E2`, e strings com escapes como `\n`."

### 2.3 Tipos derivados — vetores, inclusive matrizes (seção 4.2.2)
🗣️ Diga:
> "Vetores são declarados com `let int[3] v`. Implementei também **vetores
> multidimensionais** (matrizes), conforme o aviso do professor — `let int[3][3]
> matriz` e acesso `matriz[i][j]`. A lista de valores só pode ser atribuída na
> declaração; depois, só elemento a elemento. Vetores constantes não podem ser
> alterados — a semântica verifica isso."

💻 Mostre:
```bash
python3 jssc.py tests/basics.jss        # tem vetores 1D e matriz 2D
```

### 2.4 Tipos derivados — classes e objetos (seção 4.2.2)
🗣️ Diga:
> "Implementei classes com atributos, um `constructor` e métodos. Os atributos
> têm que vir antes dos métodos e a semântica obriga a existência de um
> construtor com o nome da classe. Objetos são criados com `new` e acessados com
> ponto; dentro dos métodos uso `this`. Objeto constante não pode ter atributo
> alterado."

💻 Mostre:
```bash
python3 jssc.py exemplos/ok4_classes.jss
python3 jssc.py exemplos/ok4_classes.jss --ast   # mostra Classe, Construtor, Metodo, this
```

### 2.5 Atribuições
🗣️ Diga:
> "Faço atribuição simples (`x = e`), composta (`+=`, `-=`, `*=`, `/=`, `%=` e
> também as lógicas `&&=` e `||=`), atribuição a elemento de vetor (`v[i] = e`) e
> a atributo de objeto (`p.x = e`). A semântica checa a compatibilidade de tipos
> em todas elas."

### 2.6 Operadores e a Tabela 1 (seção 4.3)
🗣️ Diga:
> "Implementei **todos** os operadores da Tabela 1, respeitando a precedência e a
> associatividade. No analisador sintático cada nível de precedência é uma
> função, da mais baixa (atribuição) à mais alta (unários), por isso `2 + 3 * 4`
> calcula a multiplicação primeiro automaticamente. Exponenciação e atribuição
> são associativas à direita; o resto, à esquerda."
>
> "A semântica aplica as regras de tipo da tabela: por exemplo, `%` e `**` exigem
> inteiros; os aritméticos fazem **conversão implícita para real** quando um
> operando é real; o `+` vira **concatenação** quando um operando é string; os
> relacionais e lógicos resultam em booleano. Os operadores lógicos são de
> **curto-circuito**."

💻 Mostre:
```bash
python3 jssc.py tests/operators.jss
```

### 2.7 Funções (seção 4.4)
🗣️ Diga:
> "Funções têm tipo de retorno, parâmetros e podem ser **recursivas** ou chamar
> outras. Funções `void` não precisam de `return`. A semântica garante: o tipo de
> retorno bate com o `return`, o tipo de retorno não pode ser vetor, os argumentos
> conferem em número e tipo, funções têm escopo global e o nome não pode colidir
> com outra função, variável ou constante."

💻 Mostre (erros que comprovam as checagens):
```bash
echo 'function int f(int a){return a;} function void main(){ f(1,2); }' | python3 jssc.py  # nº de args
echo 'function int f(){ return true; }'                                 | python3 jssc.py  # tipo de retorno
```

### 2.8 Funções nativas (seção 4.5)
🗣️ Diga:
> "O compilador já reconhece as nativas: `input(...)` para leitura, que exige
> variáveis; `console.log(...)` para saída, com lista de expressões; e as
> conversões `int()`, `real()`, `str()` e `bool()`, com as regras de
> intercâmbio entre numéricos e booleanos e a conversão de qualquer primitivo
> para string."

### 2.9 Controle de fluxo (seção 4.6)
🗣️ Diga:
> "Tenho `if / else if / else`, `while` e `for` — inclusive aninhados — com
> `break`. As condições têm que ser booleanas, e a semântica garante que `break`
> só aparece dentro de um laço. O `for` aceita listas separadas por vírgula na
> inicialização e na atualização."

💻 Mostre:
```bash
python3 jssc.py tests/control_flow.jss
echo 'function void main(){ break; }' | python3 jssc.py   # break fora de laço
```

### 2.10 Programa (seção 4.7)
🗣️ Diga:
> "Um programa é um conjunto de funções, classes e declarações globais. A função
> `main` é **facultativa**, como a especificação diz. Só aceito comentários de
> linha com `//`, e os arquivos têm extensão `.jss`."

---

## PARTE 3 — Detecção de erros indicando a linha (item 3.1.c.II)

🗣️ Diga:
> "Em qualquer das três fases, se houver erro, o compilador para e aponta a
> linha. Posso mostrar um de cada tipo — ou o senhor pode pedir uma modificação
> em um código que rode."

💻 Mostre os três tipos:
```bash
python3 jssc.py exemplos/erro_lexico.jss        # Erro lexico na linha 5
python3 jssc.py exemplos/erro_sintatico.jss     # Erro sintatico na linha 4
python3 jssc.py exemplos/erro_semantico.jss     # Erro semantico na linha 5 (var não declarada)
python3 jssc.py exemplos/erro_tipo.jss          # Erro semantico na linha 5 (tipo incompatível)
```

🗣️ Se pedirem para "quebrar" um código ao vivo: pegue um exemplo que funciona,
apague um `;` ou um `)`, ou troque um tipo, e rode de novo — vai aparecer o erro
com a linha. Para corrigir, é só desfazer.

---

## PARTE 4 — O código, em uma frase cada (se perguntarem)

- **`lexer.py`** — análise léxica: `tokenizar()` transforma o texto em tokens,
  guardando a linha de cada um.
- **`jss_parser.py`** — análise sintática por descida recursiva: uma função por
  regra da gramática; monta a árvore (cada nó guarda a linha).
- **`semantic.py`** — análise semântica: percorre a árvore em duas passagens
  (primeiro registra funções/classes/globais, depois confere os corpos),
  mantendo uma pilha de escopos e uma tabela de tipos.
- **`jssc.py`** — o programa de linha de comando que encadeia as três fases.

---

## PARTE 5 — Encerramento proativo (feche você mesmo)

🗣️ Diga:
> "Resumindo: o front-end está completo — léxico, sintático e semântico —, roda
> por linha de comando como a especificação pede, cobre todos os tipos
> (primitivos, vetores inclusive matrizes, e classes), todos os operadores da
> Tabela 1 com a precedência correta, as funções declaradas e nativas, e todos os
> controles de fluxo. Os erros das três fases são reportados com a linha. O
> próximo passo é o back-end, que vai traduzir essa árvore para código
> intermediário."

---

## Checklist antes de apresentar
- [ ] Terminal aberto na pasta do projeto; `python3 --version` funciona.
- [ ] Rodei os exemplos `ok1`..`ok4` e os `tests/` (todos dão sucesso).
- [ ] Rodei os quatro `erro_*` (cada um aponta a linha certa).
- [ ] Li as Partes 0, 1 e 2 deste guia pelo menos uma vez.
