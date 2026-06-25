"""
Analisador Semantico da linguagem JSS.

Percorre a arvore sintatica (AST) verificando as regras de SIGNIFICADO que a
gramatica nao consegue garantir sozinha:

- escopos (global e de bloco) e visibilidade dos identificadores;
- declaracao antes do uso e proibicao de redeclaracao no mesmo escopo;
- tipagem forte das expressoes, seguindo a Tabela 1 de precedencia/tipos;
- conversoes implicitas (int -> real; concatenacao para str);
- constantes nao podem ser reatribuidas;
- chamadas de funcao/metodo com numero e tipo de argumentos corretos;
- 'return' compativel com o tipo da funcao; 'break' so dentro de laco;
- vetores (inclusive multidimensionais) e objetos/classes.

Trabalha em duas passagens: primeiro registra funcoes, classes e variaveis
globais (para permitir uso antes da declaracao e recursao); depois analisa os
corpos.
"""

ERRO = "<erro>"                      # tipo sentinela: evita erros em cascata
PRIMITIVOS = {"int", "real", "str", "bool"}


class ErroSemantico(Exception):
    def __init__(self, linha, mensagem):
        self.linha = linha
        self.mensagem = mensagem
        super().__init__(f"Erro semantico na linha {linha}: {mensagem}")


class Analisador:
    def __init__(self, arvore):
        self.arvore = arvore
        self.escopos = []            # pilha de dicionarios nome -> info
        self.funcoes = {}            # nome -> {ret, params, linha}
        self.classes = {}            # nome -> {atributos, metodos, construtor}
        self.funcao_atual = None     # info da funcao/metodo em analise
        self.classe_atual = None     # nome da classe atual (para 'this')
        self.profundidade_loop = 0
        self.linha_atual = 1

    def analisar(self):
        self.escopos.append({})      # escopo global
        self.coletar()
        for decl in self.arvore.filhos:
            if decl.tipo == "Funcao":
                self.analisar_funcao(decl)
            elif decl.tipo == "Classe":
                self.analisar_classe(decl)
            elif decl.tipo == "Declaracao":
                self.checar_inicializadores(decl)
        self.escopos.pop()

    # erros e tipos

    def erro(self, linha, mensagem):
        raise ErroSemantico(linha if linha is not None else self.linha_atual, mensagem)

    def eh_array(self, t):
        return t.endswith("[]")

    def base_array(self, t):
        return t[:-2]

    def eh_numerico(self, t):
        return t in ("int", "real")

    def eh_classe(self, t):
        return t in self.classes

    def compativel_atribuicao(self, destino, origem):
        if destino == ERRO or origem == ERRO:
            return True
        if destino == origem:
            return True
        if destino == "real" and origem == "int":      # alargamento implicito
            return True
        if origem == "null" and self.eh_classe(destino):
            return True
        return False

    def validar_tipo(self, tipo, linha):
        base = tipo
        while base.endswith("[]"):
            base = base[:-2]
        if base in PRIMITIVOS or base == "void" or base in self.classes:
            return
        self.erro(linha, f"tipo desconhecido: '{tipo}'")

    # escopos

    def declarar(self, nome, tipo, categoria, linha):
        if nome in self.escopos[-1]:
            self.erro(linha, f"'{nome}' ja foi declarado neste escopo")
        if len(self.escopos) > 1 and nome in self.funcoes:
            self.erro(linha, f"o nome '{nome}' ja pertence a uma funcao")
        self.escopos[-1][nome] = {"tipo": tipo, "categoria": categoria, "linha": linha}

    def buscar(self, nome):
        for escopo in reversed(self.escopos):
            if nome in escopo:
                return escopo[nome]
        return None

    # passagem 1: coleta de declaracoes globais

    def coletar(self):
        for decl in self.arvore.filhos:
            if decl.tipo == "Funcao":
                self.registrar_funcao(decl)
            elif decl.tipo == "Classe":
                self.registrar_classe(decl)
            elif decl.tipo == "Declaracao":
                self.registrar_global(decl)

    def extrair_params(self, params_no):
        params = []
        for p in params_no.filhos:
            tipo, nome = p.valor.rsplit(" ", 1)
            params.append((tipo, nome, p.linha))
        return params

    def tipo_da_declaracao(self, decl):
        base = None
        ndims = 0
        for f in decl.filhos:
            if f.tipo == "Tipo":
                base = f.valor
            elif f.tipo == "Dimensao":
                ndims += 1
        return base + "[]" * ndims

    def registrar_funcao(self, decl):
        nome = decl.valor
        if nome in self.funcoes:
            self.erro(decl.linha, f"a funcao '{nome}' ja foi declarada")
        if nome in self.escopos[0]:
            self.erro(decl.linha, f"o nome '{nome}' ja pertence a uma variavel global")
        self.funcoes[nome] = {"ret": decl.filhos[0].valor,
                              "params": self.extrair_params(decl.filhos[1]),
                              "linha": decl.linha}

    def registrar_global(self, decl):
        tipo = self.tipo_da_declaracao(decl)
        categoria = decl.valor
        for f in decl.filhos:
            if f.tipo != "Var":
                continue
            if f.valor in self.escopos[0]:
                self.erro(f.linha, f"'{f.valor}' ja foi declarado no escopo global")
            if f.valor in self.funcoes:
                self.erro(f.linha, f"o nome '{f.valor}' ja pertence a uma funcao")
            self.escopos[0][f.valor] = {"tipo": tipo, "categoria": categoria, "linha": f.linha}

    def registrar_classe(self, decl):
        nome = decl.valor
        if nome in self.classes:
            self.erro(decl.linha, f"a classe '{nome}' ja foi declarada")
        info = {"atributos": {}, "metodos": {}, "construtor": None}
        viu_metodo = False
        for m in decl.filhos:
            if m.tipo == "Atributo":
                if viu_metodo:
                    self.erro(m.linha, "os atributos devem vir antes dos metodos")
                if m.valor in info["atributos"]:
                    self.erro(m.linha, f"atributo '{m.valor}' duplicado")
                t = m.filhos[0].valor + "[]" * sum(1 for x in m.filhos if x.tipo == "Dimensao")
                info["atributos"][m.valor] = t
            elif m.tipo == "Construtor":
                viu_metodo = True
                if info["construtor"] is not None:
                    self.erro(m.linha, "uma classe deve ter apenas um construtor")
                if m.valor != nome:
                    self.erro(m.linha, f"o construtor deve ter o nome da classe ('{nome}')")
                info["construtor"] = {"params": self.extrair_params(m.filhos[0])}
            elif m.tipo == "Metodo":
                viu_metodo = True
                if m.valor in info["metodos"]:
                    self.erro(m.linha, f"metodo '{m.valor}' duplicado")
                info["metodos"][m.valor] = {"ret": m.filhos[0].valor,
                                            "params": self.extrair_params(m.filhos[1])}
        if info["construtor"] is None:
            self.erro(decl.linha, f"a classe '{nome}' precisa de um construtor")
        self.classes[nome] = info

    # passagem 2: analise dos corpos

    def analisar_funcao(self, decl):
        ret = decl.filhos[0].valor
        self.validar_tipo(ret, decl.linha)
        if self.eh_array(ret):
            self.erro(decl.linha, "o tipo de retorno de uma funcao nao pode ser vetor")
        if decl.valor == "main" and decl.filhos[1].filhos:
            self.erro(decl.linha, "a funcao main nao pode ter parametros")
        self.classe_atual = None
        self.analisar_subrotina(decl.filhos[1], decl.filhos[2], ret, decl.linha)

    def analisar_classe(self, decl):
        nome = decl.valor
        self.classe_atual = nome
        for t in self.classes[nome]["atributos"].values():
            self.validar_tipo(t, decl.linha)
        for m in decl.filhos:
            if m.tipo == "Construtor":
                self.analisar_subrotina(m.filhos[0], m.filhos[1], "void", m.linha)
            elif m.tipo == "Metodo":
                ret = m.filhos[0].valor
                self.validar_tipo(ret, m.linha)
                if self.eh_array(ret):
                    self.erro(m.linha, "o tipo de retorno de um metodo nao pode ser vetor")
                self.analisar_subrotina(m.filhos[1], m.filhos[2], ret, m.linha)
        self.classe_atual = None

    def analisar_subrotina(self, params_no, corpo, ret, linha):
        anterior = self.funcao_atual
        self.funcao_atual = {"ret": ret}
        self.escopos.append({})
        for (tipo, nome, plinha) in self.extrair_params(params_no):
            self.validar_tipo(tipo, plinha)
            self.declarar(nome, tipo, "param", plinha)
        self.analisar_bloco(corpo, novo_escopo=False)
        self.escopos.pop()
        self.funcao_atual = anterior
        # funcao/metodo com retorno (nao-void) precisa ter um 'return' com valor
        if ret != "void" and not self.tem_return_com_valor(corpo):
            self.erro(linha, f"uma funcao com retorno '{ret}' precisa ter um 'return' com valor")

    def tem_return_com_valor(self, no):
        if no.tipo == "Return":
            return len(no.filhos) > 0
        return any(self.tem_return_com_valor(f) for f in no.filhos)

    def analisar_bloco(self, bloco, novo_escopo=True):
        if novo_escopo:
            self.escopos.append({})
        for cmd in bloco.filhos:
            self.analisar_comando(cmd)
        if novo_escopo:
            self.escopos.pop()

    def analisar_comando(self, no):
        self.linha_atual = no.linha or self.linha_atual
        t = no.tipo
        if t == "Declaracao":
            self.analisar_declaracao_local(no)
        elif t == "If":
            self.analisar_if(no)
        elif t == "While":
            self.analisar_while(no)
        elif t == "For":
            self.analisar_for(no)
        elif t == "Return":
            self.analisar_return(no)
        elif t == "Break":
            self.analisar_break(no)
        elif t == "Bloco":
            self.analisar_bloco(no)
        elif t == "ExprStmt":
            self.tipo_de(no.filhos[0])

    def analisar_declaracao_local(self, decl):
        tipo_decl = self.tipo_da_declaracao(decl)
        self.validar_tipo(tipo_decl, decl.linha)
        for f in decl.filhos:
            if f.tipo == "Dimensao":
                td = self.tipo_de(f.filhos[0])
                if td not in ("int", ERRO):
                    self.erro(decl.linha, "a dimensao de um vetor deve ser int")
        categoria = decl.valor
        for f in decl.filhos:
            if f.tipo != "Var":
                continue
            init = f.filhos[0] if f.filhos else None
            if init is not None:
                self.checar_init(tipo_decl, init, f.linha)
            elif categoria == "const":
                self.erro(f.linha, f"a constante '{f.valor}' precisa ser inicializada")
            self.declarar(f.valor, tipo_decl, categoria, f.linha)

    def checar_inicializadores(self, decl):
        # usado para variaveis globais (ja registradas na passagem 1)
        tipo_decl = self.tipo_da_declaracao(decl)
        self.validar_tipo(tipo_decl, decl.linha)
        for f in decl.filhos:
            if f.tipo == "Var" and f.filhos:
                self.checar_init(tipo_decl, f.filhos[0], f.linha)
            elif f.tipo == "Var" and decl.valor == "const" and not f.filhos:
                self.erro(f.linha, f"a constante '{f.valor}' precisa ser inicializada")

    def checar_init(self, tipo_decl, init, linha):
        if self.eh_array(tipo_decl) and init.tipo == "Vetor":
            base = self.base_array(tipo_decl)
            for e in init.filhos:
                te = self.tipo_de(e)
                if not self.compativel_atribuicao(base, te):
                    self.erro(e.linha or linha,
                              f"elemento do vetor incompativel: esperava '{base}', obteve '{te}'")
            return
        ti = self.tipo_de(init)
        if not self.compativel_atribuicao(tipo_decl, ti):
            self.erro(linha, f"tipo incompativel: '{tipo_decl}' nao pode receber '{ti}'")

    def analisar_if(self, no):
        for ramo in no.filhos:
            if ramo.tipo == "Cond":
                self.exigir_bool(ramo.filhos[0], "a condicao do if deve ser booleana")
            elif ramo.tipo == "Entao":
                self.analisar_bloco(ramo.filhos[0])
            elif ramo.tipo == "SenaoSe":
                self.exigir_bool(ramo.filhos[0].filhos[0], "a condicao do else if deve ser booleana")
                self.analisar_bloco(ramo.filhos[1].filhos[0])
            elif ramo.tipo == "Senao":
                self.analisar_bloco(ramo.filhos[0])

    def analisar_while(self, no):
        cond, corpo = no.filhos
        self.exigir_bool(cond.filhos[0], "a condicao do while deve ser booleana")
        self.profundidade_loop += 1
        self.analisar_bloco(corpo)
        self.profundidade_loop -= 1

    def analisar_for(self, no):
        init, cond, upd, corpo = no.filhos
        self.escopos.append({})
        for c in init.filhos:
            if c.tipo == "Declaracao":
                self.analisar_declaracao_local(c)
            else:
                self.tipo_de(c)
        for c in cond.filhos:
            self.exigir_bool(c, "a condicao do for deve ser booleana")
        for c in upd.filhos:
            self.tipo_de(c)
        self.profundidade_loop += 1
        self.analisar_bloco(corpo)
        self.profundidade_loop -= 1
        self.escopos.pop()

    def analisar_return(self, no):
        esperado = self.funcao_atual["ret"]
        if no.filhos:
            t = self.tipo_de(no.filhos[0])
            if esperado == "void":
                self.erro(no.linha, "uma funcao void nao deve retornar um valor")
            elif not self.compativel_atribuicao(esperado, t):
                self.erro(no.linha, f"retorno incompativel: esperava '{esperado}', obteve '{t}'")
        elif esperado != "void":
            self.erro(no.linha, f"esta funcao deve retornar um valor do tipo '{esperado}'")

    def analisar_break(self, no):
        if self.profundidade_loop == 0:
            self.erro(no.linha, "'break' so pode ser usado dentro de while ou for")

    def exigir_bool(self, expr, mensagem):
        t = self.tipo_de(expr)
        if t not in ("bool", ERRO):
            self.erro(expr.linha or self.linha_atual, mensagem)

    # tipagem de expressoes

    def tipo_de(self, no):
        t = no.tipo
        if t == "Int":
            return "int"
        if t == "Real":
            return "real"
        if t == "Str":
            return "str"
        if t == "Bool":
            return "bool"
        if t == "Null":
            return "null"
        if t == "This":
            return self.tipo_this(no)
        if t == "Id":
            return self.tipo_id(no)
        if t == "Vetor":
            return self.tipo_vetor(no)
        if t == "OpUnario":
            return self.tipo_opunario(no)
        if t == "OpBin":
            return self.tipo_opbin(no)
        if t == "Atrib":
            return self.tipo_atrib(no)
        if t == "Cast":
            return self.tipo_cast(no)
        if t == "New":
            return self.tipo_new(no)
        if t == "Indice":
            return self.tipo_indice(no)
        if t == "Membro":
            return self.tipo_membro(no)
        if t == "Chamada":
            return self.tipo_chamada(no)
        return ERRO

    def tipo_this(self, no):
        if self.classe_atual is None:
            self.erro(no.linha, "'this' so pode ser usado dentro de metodos de uma classe")
        return self.classe_atual

    def tipo_id(self, no):
        sym = self.buscar(no.valor)
        if sym is not None:
            return sym["tipo"]
        if no.valor in self.funcoes:
            self.erro(no.linha, f"a funcao '{no.valor}' deve ser chamada com '()'")
        if no.valor in self.classes:
            self.erro(no.linha, f"'{no.valor}' e uma classe e nao um valor")
        self.erro(no.linha, f"identificador '{no.valor}' nao declarado")

    def tipo_vetor(self, no):
        if not no.filhos:
            return ERRO
        return self.tipo_de(no.filhos[0]) + "[]"

    def tipo_opunario(self, no):
        op = no.valor
        t = self.tipo_de(no.filhos[0])
        if t == ERRO:
            return ERRO
        if op == "!":
            if t != "bool":
                self.erro(no.linha, "o operador '!' exige um booleano")
            return "bool"
        # +, -, ++, --
        if op in ("++", "--") and no.filhos[0].tipo not in ("Id", "Indice", "Membro"):
            self.erro(no.linha, f"o operador '{op}' exige uma variavel")
        if not self.eh_numerico(t):
            self.erro(no.linha, f"o operador '{op}' exige int ou real")
        return t

    def tipo_opbin(self, no):
        op = no.valor
        te = self.tipo_de(no.filhos[0])
        td = self.tipo_de(no.filhos[1])
        if te == ERRO or td == ERRO:
            return ERRO
        if op == "+":
            if te == "str" or td == "str":
                if self.eh_array(te) or self.eh_array(td):
                    self.erro(no.linha, "nao da para concatenar vetores")
                return "str"
            return self.tipo_aritmetico(no, op, te, td)
        if op in ("-", "*", "/"):
            return self.tipo_aritmetico(no, op, te, td)
        if op in ("%", "**"):
            if not (te == "int" and td == "int"):
                self.erro(no.linha, f"o operador '{op}' exige dois inteiros")
            return "int"
        if op in (">", ">=", "<", "<="):
            if self.eh_array(te) or self.eh_array(td):
                self.erro(no.linha, f"o operador '{op}' nao se aplica a vetores")
            return "bool"
        if op in ("==", "!="):
            return "bool"
        if op in ("&&", "||"):
            if te != "bool" or td != "bool":
                self.erro(no.linha, f"o operador '{op}' exige operandos booleanos")
            return "bool"
        return ERRO

    def tipo_aritmetico(self, no, op, te, td):
        if not (self.eh_numerico(te) and self.eh_numerico(td)):
            self.erro(no.linha, f"o operador '{op}' exige operandos numericos (int ou real)")
        return "real" if (te == "real" or td == "real") else "int"

    def tipo_atrib(self, no):
        lhs, rhs = no.filhos
        op = no.valor
        if lhs.tipo not in ("Id", "Indice", "Membro"):
            self.erro(no.linha, "o lado esquerdo de uma atribuicao deve ser uma variavel")
        if self.lvalue_const(lhs):
            self.erro(no.linha, "nao e possivel alterar uma constante")
        tipo_lhs = self.tipo_de(lhs)
        tipo_rhs = self.tipo_de(rhs)
        if op == "=":
            if self.eh_array(tipo_lhs) and rhs.tipo == "Vetor":
                self.erro(no.linha, "uma lista so pode ser atribuida a um vetor na declaracao")
            if not self.compativel_atribuicao(tipo_lhs, tipo_rhs):
                self.erro(no.linha, f"atribuicao incompativel: '{tipo_lhs}' nao recebe '{tipo_rhs}'")
        elif op in ("&&=", "||="):
            if tipo_lhs != "bool" or tipo_rhs != "bool":
                self.erro(no.linha, f"o operador '{op}' exige operandos booleanos")
        elif op == "%=":
            if not (tipo_lhs == "int" and tipo_rhs == "int") and ERRO not in (tipo_lhs, tipo_rhs):
                self.erro(no.linha, "o operador '%=' exige inteiros")
        else:  # += -= *= /=
            if ERRO not in (tipo_lhs, tipo_rhs):
                if op == "+=" and tipo_lhs == "str":
                    pass
                elif not (self.eh_numerico(tipo_lhs) and self.eh_numerico(tipo_rhs)):
                    self.erro(no.linha, f"o operador '{op}' exige operandos numericos")
        return tipo_lhs

    def lvalue_const(self, no):
        while no.tipo in ("Indice", "Membro"):
            no = no.filhos[0]
        if no.tipo == "Id":
            sym = self.buscar(no.valor)
            return sym is not None and sym["categoria"] == "const"
        return False

    def tipo_cast(self, no):
        alvo = no.valor
        t = self.tipo_de(no.filhos[0])
        if t == ERRO:
            return alvo
        if self.eh_array(t) or self.eh_classe(t):
            self.erro(no.linha, f"nao da para converter '{t}' para '{alvo}'")
        if alvo == "str":
            return "str"
        if t == "str":
            self.erro(no.linha, f"nao da para converter 'str' para '{alvo}'")
        return alvo

    def tipo_new(self, no):
        cls = no.valor
        args = no.filhos[0].filhos
        if cls not in self.classes:
            self.erro(no.linha, f"classe '{cls}' nao declarada")
        ctor = self.classes[cls]["construtor"]
        self.checar_args(no.linha, ctor["params"], args, f"o construtor de '{cls}'")
        return cls

    def tipo_indice(self, no):
        tb = self.tipo_de(no.filhos[0])
        ti = self.tipo_de(no.filhos[1])
        if ti not in ("int", ERRO):
            self.erro(no.linha, "o indice de um vetor deve ser int")
        if tb == ERRO:
            return ERRO
        if not self.eh_array(tb):
            self.erro(no.linha, f"'{tb}' nao e um vetor para ser indexado")
        return self.base_array(tb)

    def tipo_membro(self, no):
        tb = self.tipo_de(no.filhos[0])
        membro = no.valor
        if tb == ERRO:
            return ERRO
        if not self.eh_classe(tb):
            self.erro(no.linha, f"'{tb}' nao e um objeto, entao nao tem o membro '{membro}'")
        atributos = self.classes[tb]["atributos"]
        if membro in atributos:
            return atributos[membro]
        if membro in self.classes[tb]["metodos"]:
            self.erro(no.linha, f"o metodo '{membro}' deve ser chamado com '()'")
        self.erro(no.linha, f"a classe '{tb}' nao tem o atributo '{membro}'")

    def tipo_chamada(self, no):
        callee = no.filhos[0]
        args = no.filhos[1].filhos
        # console.log(...) nativa
        if callee.tipo == "Membro":
            base = callee.filhos[0]
            if (base.tipo == "Id" and base.valor == "console"
                    and callee.valor == "log" and self.buscar("console") is None):
                for a in args:
                    self.tipo_de(a)
                return "void"
            tipo_obj = self.tipo_de(base)
            if tipo_obj == ERRO:
                for a in args:
                    self.tipo_de(a)
                return ERRO
            if not self.eh_classe(tipo_obj):
                self.erro(no.linha, f"'{tipo_obj}' nao e um objeto para chamar '{callee.valor}'")
            metodo = self.classes[tipo_obj]["metodos"].get(callee.valor)
            if metodo is None:
                self.erro(no.linha, f"a classe '{tipo_obj}' nao tem o metodo '{callee.valor}'")
            self.checar_args(no.linha, metodo["params"], args, f"o metodo '{callee.valor}'")
            return metodo["ret"]
        if callee.tipo == "Id":
            nome = callee.valor
            if nome == "input":                      # nativa: le variaveis
                for a in args:
                    if a.tipo not in ("Id", "Indice", "Membro"):
                        self.erro(no.linha, "input espera variaveis")
                    ta = self.tipo_de(a)
                    if ta not in PRIMITIVOS and ta != ERRO:
                        self.erro(no.linha, "input so le tipos primitivos")
                return "void"
            if nome in self.funcoes:
                f = self.funcoes[nome]
                self.checar_args(no.linha, f["params"], args, f"a funcao '{nome}'")
                return f["ret"]
            self.erro(no.linha, f"a funcao '{nome}' nao foi declarada")
        self.erro(no.linha, "chamada invalida")

    def checar_args(self, linha, params, args, desc):
        if len(args) != len(params):
            self.erro(linha, f"{desc} espera {len(params)} argumento(s), recebeu {len(args)}")
        for (ptipo, _pnome, _pl), a in zip(params, args):
            at = self.tipo_de(a)
            if not self.compativel_atribuicao(ptipo, at):
                self.erro(a.linha or linha,
                          f"argumento incompativel em {desc}: esperava '{ptipo}', obteve '{at}'")
