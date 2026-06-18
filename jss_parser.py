"""
Analisador Sintatico (Parser) da linguagem JSS.

Recebe a lista de tokens do lexer e verifica se eles formam um programa
gramaticalmente valido. Usa a tecnica de "descida recursiva" (recursive
descent): para cada regra da gramatica existe uma funcao que a reconhece.

Como subproduto, construimos uma Arvore Sintatica (AST) simples, que mostra
como o programa foi entendido. Ela sera usada na etapa de back-end.

Resumo da gramatica reconhecida nesta etapa (previa):

    programa     -> declaracao*
    declaracao   -> func_decl | var_decl
    func_decl    -> 'function' tipo_ret ID '(' params? ')' bloco
    var_decl     -> ('let'|'const') tipo ('[' expr ']')? ID ('=' expr)?
                                              (',' ID ('=' expr)?)* ';'
    bloco        -> '{' comando* '}'
    comando      -> var_decl | if | while | for | return | break
                  | bloco | expr ';'
    expr (com precedencia, da mais baixa para a mais alta):
        atribuicao  =  +=  -=  *=  /=  %=     (associativo a direita)
        ||
        &&
        ==  !=  >  >=  <  <=
        +  -
        *  /  %
        **                                    (associativo a direita)
        unario:  !  +  -  ++  --              (prefixado)
        posfixo: chamada()  indice[]  membro.x
        primario: literais, ID, (expr), conversao tipo(expr), new, [vetor]

Ainda NAO cobertos nesta previa (proxima etapa): declaracao de classes e
analise semantica.
"""


# No da arvore sintatica

class No:
    """Um no generico da arvore. `tipo` e o rotulo; `valor` aparece nas folhas."""

    def __init__(self, tipo, *filhos, valor=None):
        self.tipo = tipo
        self.valor = valor
        self.filhos = [f for f in filhos if f is not None]


class ErroSintatico(Exception):
    """Erro encontrado durante a analise sintatica (estrutura invalida)."""

    def __init__(self, linha, mensagem):
        self.linha = linha
        self.mensagem = mensagem
        super().__init__(f"Erro sintatico na linha {linha}: {mensagem}")


# Parser

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    # utilitarios de navegacao 

    def atual(self):
        return self.tokens[self.pos]

    def avancar(self):
        tok = self.tokens[self.pos]
        if tok.tipo != "EOF":
            self.pos += 1
        return tok

    def checar_valor(self, *valores):
        tok = self.atual()
        return tok.tipo != "EOF" and tok.valor in valores

    def checar_tipo(self, *tipos):
        return self.atual().tipo in tipos

    def consumir_valor(self, valor, oque=None):
        tok = self.atual()
        if tok.tipo != "EOF" and tok.valor == valor:
            return self.avancar()
        esperado = oque or f"'{valor}'"
        raise ErroSintatico(tok.linha,
                            f"esperava {esperado}, mas encontrei '{self._desc(tok)}'")

    def consumir_tipo(self, tipo, oque):
        tok = self.atual()
        if tok.tipo == tipo:
            return self.avancar()
        raise ErroSintatico(tok.linha,
                            f"esperava {oque}, mas encontrei '{self._desc(tok)}'")

    @staticmethod
    def _desc(tok):
        return "fim do arquivo" if tok.tipo == "EOF" else tok.valor

    # programa e declaracoes 

    def parse_programa(self):
        decls = []
        while not self.checar_tipo("EOF"):
            decls.append(self.parse_declaracao())
        return No("Programa", *decls)

    def parse_declaracao(self):
        if self.checar_valor("function"):
            return self.parse_funcao()
        if self.checar_valor("let", "const"):
            return self.parse_var_decl()
        tok = self.atual()
        raise ErroSintatico(
            tok.linha,
            "esperava uma declaracao ('function', 'let' ou 'const'), "
            f"mas encontrei '{self._desc(tok)}'")

    def parse_funcao(self):
        self.consumir_valor("function")
        tipo_ret = self.parse_tipo_retorno()
        nome = self.consumir_tipo("ID", "o nome da funcao")
        self.consumir_valor("(", "'(' apos o nome da funcao")
        params = self.parse_parametros()
        self.consumir_valor(")", "')' para fechar os parametros")
        corpo = self.parse_bloco()
        return No("Funcao",
                  No("Retorno", valor=tipo_ret),
                  No("Params", *params),
                  corpo,
                  valor=nome.valor)

    def parse_tipo_retorno(self):
        if self.checar_valor("void"):
            self.avancar()
            return "void"
        return self.parse_tipo()

    def parse_tipo(self):
        tok = self.atual()
        if tok.tipo == "TIPO":          # int, real, str, bool
            self.avancar()
            return tok.valor
        if tok.tipo == "ID":            # nome de classe usado como tipo
            self.avancar()
            return tok.valor
        raise ErroSintatico(
            tok.linha,
            "esperava um tipo (int, real, str, bool ou nome de classe), "
            f"mas encontrei '{self._desc(tok)}'")

    def parse_parametros(self):
        params = []
        if self.checar_valor(")"):
            return params
        while True:
            tipo = self.parse_tipo()
            sufixo = ""
            if self.checar_valor("["):          # parametro do tipo vetor: int[] v
                self.avancar()
                self.consumir_valor("]", "']' na declaracao de vetor do parametro")
                sufixo = "[]"
            nome = self.consumir_tipo("ID", "o nome do parametro")
            params.append(No("Param", valor=f"{tipo}{sufixo} {nome.valor}"))
            if self.checar_valor(","):
                self.avancar()
                continue
            break
        return params

    def parse_bloco(self):
        self.consumir_valor("{", "'{' para abrir o bloco")
        comandos = []
        while not self.checar_valor("}") and not self.checar_tipo("EOF"):
            comandos.append(self.parse_comando())
        self.consumir_valor("}", "'}' para fechar o bloco")
        return No("Bloco", *comandos)

    def parse_var_decl(self, exigir_ponto_virgula=True):
        palavra = self.avancar()            # 'let' ou 'const'
        tipo = self.parse_tipo()
        dims = []
        while self.checar_valor("["):       # dimensoes: tipo[e] (1D) ou tipo[e][e] (matriz)
            self.avancar()
            dims.append(self.parse_expressao())
            self.consumir_valor("]", "']' para fechar a dimensao do vetor")
        itens = []
        while True:
            nome = self.consumir_tipo("ID", "o nome da variavel")
            init = None
            if self.checar_valor("="):
                self.avancar()
                init = self.parse_expressao()
            itens.append(No("Var", init, valor=nome.valor))
            if self.checar_valor(","):
                self.avancar()
                continue
            break
        if exigir_ponto_virgula:
            self.consumir_valor(";", "';' no fim da declaracao")
        filhos = [No("Tipo", valor=tipo)]
        for d in dims:
            filhos.append(No("Dimensao", d))
        filhos.extend(itens)
        return No("Declaracao", *filhos, valor=palavra.valor)

    # comandos

    def parse_comando(self):
        if self.checar_valor("let", "const"):
            return self.parse_var_decl()
        if self.checar_valor("if"):
            return self.parse_if()
        if self.checar_valor("while"):
            return self.parse_while()
        if self.checar_valor("for"):
            return self.parse_for()
        if self.checar_valor("return"):
            return self.parse_return()
        if self.checar_valor("break"):
            self.avancar()
            self.consumir_valor(";", "';' apos break")
            return No("Break")
        if self.checar_valor("{"):
            return self.parse_bloco()
        # caso geral: comando de expressao (atribuicao, chamada de funcao...)
        expr = self.parse_expressao()
        self.consumir_valor(";", "';' no fim do comando")
        return No("ExprStmt", expr)

    def parse_if(self):
        self.consumir_valor("if")
        self.consumir_valor("(", "'(' apos if")
        cond = self.parse_expressao()
        self.consumir_valor(")", "')' apos a condicao do if")
        entao = self.parse_bloco()
        filhos = [No("Cond", cond), No("Entao", entao)]
        while self.checar_valor("else"):
            self.avancar()
            if self.checar_valor("if"):     # else if (...)
                self.consumir_valor("if")
                self.consumir_valor("(", "'(' apos else if")
                c2 = self.parse_expressao()
                self.consumir_valor(")", "')' apos a condicao do else if")
                b2 = self.parse_bloco()
                filhos.append(No("SenaoSe", No("Cond", c2), No("Entao", b2)))
            else:                           # else { ... }
                filhos.append(No("Senao", self.parse_bloco()))
                break
        return No("If", *filhos)

    def parse_while(self):
        self.consumir_valor("while")
        self.consumir_valor("(", "'(' apos while")
        cond = self.parse_expressao()
        self.consumir_valor(")", "')' apos a condicao do while")
        return No("While", No("Cond", cond), self.parse_bloco())

    def parse_for(self):
        # Conforme a especificacao, cada uma das tres partes do for pode conter
        # uma LISTA separada por virgula (atribuicoes ou, no init, uma declaracao).
        self.consumir_valor("for")
        self.consumir_valor("(", "'(' apos for")
        # 1) inicializacao: vazia, uma declaracao (let/const), ou lista de atribuicoes
        init = No("Init")
        if self.checar_valor("let", "const"):
            init.filhos.append(self.parse_var_decl(exigir_ponto_virgula=False))
        elif not self.checar_valor(";"):
            init.filhos.append(self.parse_expressao())
            while self.checar_valor(","):
                self.avancar()
                init.filhos.append(self.parse_expressao())
        self.consumir_valor(";", "';' apos a inicializacao do for")
        # 2) condicao (opcional)
        cond = No("Cond")
        if not self.checar_valor(";"):
            cond.filhos.append(self.parse_expressao())
            while self.checar_valor(","):
                self.avancar()
                cond.filhos.append(self.parse_expressao())
        self.consumir_valor(";", "';' apos a condicao do for")
        # 3) atualizacao (opcional): lista de atribuicoes separadas por virgula
        upd = No("Update")
        if not self.checar_valor(")"):
            upd.filhos.append(self.parse_expressao())
            while self.checar_valor(","):
                self.avancar()
                upd.filhos.append(self.parse_expressao())
        self.consumir_valor(")", "')' para fechar o for")
        corpo = self.parse_bloco()
        return No("For", init, cond, upd, corpo)

    def parse_return(self):
        self.consumir_valor("return")
        expr = None
        if not self.checar_valor(";"):
            expr = self.parse_expressao()
        self.consumir_valor(";", "';' apos o return")
        return No("Return", expr)

    # expressoes (em ordem de precedencia)

    def parse_expressao(self):
        return self.parse_atribuicao()

    def parse_atribuicao(self):
        esq = self.parse_ou()
        if self.checar_valor("=", "+=", "-=", "*=", "/=", "%=", "&&=", "||="):
            op = self.avancar().valor
            direita = self.parse_atribuicao()      # associativo a direita
            return No("Atrib", esq, direita, valor=op)
        return esq

    def parse_ou(self):
        no = self.parse_e()
        while self.checar_valor("||"):
            op = self.avancar().valor
            no = No("OpBin", no, self.parse_e(), valor=op)
        return no

    def parse_e(self):
        no = self.parse_comparacao()
        while self.checar_valor("&&"):
            op = self.avancar().valor
            no = No("OpBin", no, self.parse_comparacao(), valor=op)
        return no

    def parse_comparacao(self):
        no = self.parse_aditivo()
        while self.checar_valor("==", "!=", ">", ">=", "<", "<="):
            op = self.avancar().valor
            no = No("OpBin", no, self.parse_aditivo(), valor=op)
        return no

    def parse_aditivo(self):
        no = self.parse_multiplicativo()
        while self.checar_valor("+", "-"):
            op = self.avancar().valor
            no = No("OpBin", no, self.parse_multiplicativo(), valor=op)
        return no

    def parse_multiplicativo(self):
        no = self.parse_exponenciacao()
        while self.checar_valor("*", "/", "%"):
            op = self.avancar().valor
            no = No("OpBin", no, self.parse_exponenciacao(), valor=op)
        return no

    def parse_exponenciacao(self):
        no = self.parse_unario()
        if self.checar_valor("**"):
            op = self.avancar().valor
            return No("OpBin", no, self.parse_exponenciacao(), valor=op)  # dir.
        return no

    def parse_unario(self):
        if self.checar_valor("!", "+", "-", "++", "--"):
            op = self.avancar().valor
            return No("OpUnario", self.parse_unario(), valor=op)
        return self.parse_posfixo()

    def parse_posfixo(self):
        no = self.parse_primario()
        while True:
            if self.checar_valor("["):              # indexacao de vetor: v[i]
                self.avancar()
                idx = self.parse_expressao()
                self.consumir_valor("]", "']' para fechar o indice do vetor")
                no = No("Indice", no, idx)
            elif self.checar_valor("."):            # acesso a membro: obj.x
                self.avancar()
                membro = self.consumir_tipo("ID", "o nome do atributo/metodo apos '.'")
                no = No("Membro", no, valor=membro.valor)
            elif self.checar_valor("("):            # chamada: f(args)
                self.avancar()
                args = self.parse_argumentos()
                self.consumir_valor(")", "')' para fechar a chamada")
                no = No("Chamada", no, No("Args", *args))
            else:
                break
        return no

    def parse_argumentos(self):
        args = []
        if self.checar_valor(")"):
            return args
        while True:
            args.append(self.parse_expressao())
            if self.checar_valor(","):
                self.avancar()
                continue
            break
        return args

    def parse_primario(self):
        tok = self.atual()

        if tok.tipo == "INT":
            self.avancar()
            return No("Int", valor=tok.valor)
        if tok.tipo == "REAL":
            self.avancar()
            return No("Real", valor=tok.valor)
        if tok.tipo == "STR":
            self.avancar()
            return No("Str", valor=f'"{tok.valor}"')
        if tok.tipo == "BOOL":
            self.avancar()
            return No("Bool", valor=tok.valor)
        if tok.tipo == "NULL":
            self.avancar()
            return No("Null")
        if tok.tipo == "TIPO":          # conversao: int(expr), real(expr)...
            self.avancar()
            self.consumir_valor("(", f"'(' apos '{tok.valor}' (conversao de tipo)")
            arg = self.parse_expressao()
            self.consumir_valor(")", "')' para fechar a conversao")
            return No("Cast", arg, valor=tok.valor)
        if tok.valor == "new":          # criacao de objeto
            self.avancar()
            classe = self.consumir_tipo("ID", "o nome da classe apos 'new'")
            self.consumir_valor("(", "'(' apos o nome da classe")
            args = self.parse_argumentos()
            self.consumir_valor(")", "')' para fechar os argumentos do construtor")
            return No("New", No("Args", *args), valor=classe.valor)
        if tok.tipo == "ID":
            self.avancar()
            return No("Id", valor=tok.valor)
        if tok.valor == "(":            # parenteses para forcar precedencia
            self.avancar()
            expr = self.parse_expressao()
            self.consumir_valor(")", "')' para fechar os parenteses")
            return expr
        if tok.valor == "[":            # literal de vetor: [e1, e2, ...]
            self.avancar()
            elementos = []
            if not self.checar_valor("]"):
                while True:
                    elementos.append(self.parse_expressao())
                    if self.checar_valor(","):
                        self.avancar()
                        continue
                    break
            self.consumir_valor("]", "']' para fechar o literal de vetor")
            return No("Vetor", *elementos)

        raise ErroSintatico(
            tok.linha, f"expressao invalida: nao esperava '{self._desc(tok)}'")


# ---------------------------------------------------------------------------
# Impressao da arvore (para o modo --ast)
# ---------------------------------------------------------------------------

def imprimir_arvore(no):
    rotulo = no.tipo if no.valor is None else f"{no.tipo} ({no.valor})"
    print(rotulo)
    _imprimir_filhos(no, "")


def _imprimir_filhos(no, prefixo):
    total = len(no.filhos)
    for idx, filho in enumerate(no.filhos):
        ultimo = idx == total - 1
        conector = "`- " if ultimo else "|- "
        rotulo = filho.tipo if filho.valor is None else f"{filho.tipo} ({filho.valor})"
        print(prefixo + conector + rotulo)
        _imprimir_filhos(filho, prefixo + ("   " if ultimo else "|  "))
