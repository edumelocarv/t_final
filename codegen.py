"""
Back-end: gera codigo intermediario JASMIN (assembly da JVM) a partir da AST.

Ideia central: a JVM e uma maquina de pilha, entao cada expressao vira uma
sequencia de "empilha operandos / opera". O mapeamento JSS -> JVM e quase 1:1:
  int  -> int (I)      real -> double (D)     bool -> boolean (Z)
  str  -> String       vetor -> array         classe JSS -> classe da JVM

O programa JSS vira uma classe (por padrao 'Programa'):
  - funcoes JSS      -> metodos static;
  - variaveis globais-> campos static;
  - comandos do topo -> executados no metodo main da JVM (entrada do programa).

Este modulo depende de o front-end ter rodado antes (a analise semantica anota
o tipo de cada expressao em `no.t`, que reaproveitamos aqui).
"""


class ErroBackend(Exception):
    pass


def descritor(tipo):
    """Tipo JSS -> descritor JVM."""
    if tipo == "int":
        return "I"
    if tipo == "bool":
        return "Z"
    if tipo == "real":
        return "D"
    if tipo == "str":
        return "Ljava/lang/String;"
    if tipo == "void":
        return "V"
    if tipo.endswith("[]"):
        return "[" + descritor(tipo[:-2])
    return "L" + tipo + ";"          # objeto de classe


def _escapar_str(conteudo):
    """Reescreve o conteudo de uma string para um literal aceito pelo Jasmin."""
    saida = []
    for ch in conteudo:
        if ch == "\\":
            saida.append("\\\\")
        elif ch == '"':
            saida.append('\\"')
        elif ch == "\n":
            saida.append("\\n")
        elif ch == "\t":
            saida.append("\\t")
        elif ch == "\r":
            saida.append("\\r")
        else:
            saida.append(ch)
    return '"' + "".join(saida) + '"'


class GeradorJasmin:
    def __init__(self, arvore, nome_classe="Programa"):
        self.arvore = arvore
        self.nome_classe = nome_classe
        self.globais = {}        # nome -> tipo
        self.funcoes = {}        # nome -> (ret, [(tipo, nome), ...])
        self.classes = {}        # nome -> {atributos, metodos, construtor}
        self.classe_atual = None # classe da instancia atual (para 'this')
        # estado do metodo atual:
        self.corpo = []
        self.escopos = []        # lista de dicts nome -> (slot, tipo)
        self.prox_slot = 0
        self.max_locals = 0
        self.n_rotulo = 0
        self.breaks = []         # pilha de rotulos de saida de laco
        self.ret_atual = "void"

    
    # utilidades
    

    def emitir(self, instr):
        self.corpo.append("    " + instr)

    def marca(self, rotulo):
        self.corpo.append(rotulo + ":")

    def rotulo(self):
        self.n_rotulo += 1
        return "L%d" % self.n_rotulo

    def novo_metodo(self):
        self.corpo = []
        self.escopos = [{}]
        self.prox_slot = 0
        self.max_locals = 0
        self.breaks = []

    def push_escopo(self):
        self.escopos.append({})

    def pop_escopo(self):
        self.escopos.pop()

    def declarar_local(self, nome, tipo):
        slot = self.prox_slot
        self.prox_slot += 2 if tipo == "real" else 1
        self.max_locals = max(self.max_locals, self.prox_slot)
        self.escopos[-1][nome] = (slot, tipo)
        return slot

    def buscar_local(self, nome):
        for e in reversed(self.escopos):
            if nome in e:
                return e[nome]
        return None

    @staticmethod
    def _params(params_no):
        res = []
        for p in params_no.filhos:
            tp, nm = p.valor.rsplit(" ", 1)
            res.append((tp, nm))
        return res

    @staticmethod
    def _tipo_decl(decl):
        base, nd = None, 0
        for f in decl.filhos:
            if f.tipo == "Tipo":
                base = f.valor
            elif f.tipo == "Dimensao":
                nd += 1
        return base + "[]" * nd

    # topo: monta a classe principal    

    def gerar(self):
        for item in self.arvore.filhos:
            if item.tipo == "Funcao":
                self.funcoes[item.valor] = (item.filhos[0].valor,
                                            self._params(item.filhos[1]))
            elif item.tipo == "Declaracao":
                tipo = self._tipo_decl(item)
                for f in item.filhos:
                    if f.tipo == "Var":
                        self.globais[f.valor] = tipo
            elif item.tipo == "Classe":
                self._coletar_classe(item)

        linhas = []
        linhas.append(".class public " + self.nome_classe)
        linhas.append(".super java/lang/Object")
        linhas.append("")
        linhas.append(".field static _scanner Ljava/util/Scanner;")
        for nome, tipo in self.globais.items():
            linhas.append(".field static %s %s" % (nome, descritor(tipo)))
        linhas.append("")
        linhas += [
            ".method public <init>()V",
            "    aload_0",
            "    invokespecial java/lang/Object/<init>()V",
            "    return",
            ".end method",
            "",
        ]
        for item in self.arvore.filhos:
            if item.tipo == "Funcao":
                linhas += self._gerar_funcao(item)
                linhas.append("")
        linhas += self._gerar_entrada()
        resultado = {self.nome_classe: "\n".join(linhas) + "\n"}
        for item in self.arvore.filhos:
            if item.tipo == "Classe":
                resultado[item.valor] = self._gerar_classe(item)
        return resultado

    def _coletar_classe(self, decl):
        nome = decl.valor
        info = {"atributos": {}, "metodos": {}, "construtor": []}
        for m in decl.filhos:
            if m.tipo == "Atributo":
                info["atributos"][m.valor] = m.filhos[0].valor
            elif m.tipo == "Construtor":
                info["construtor"] = self._params(m.filhos[0])
            elif m.tipo == "Metodo":
                info["metodos"][m.valor] = (m.filhos[0].valor, self._params(m.filhos[1]))
        self.classes[nome] = info

    def _gerar_classe(self, decl):
        nome = decl.valor
        info = self.classes[nome]
        linhas = [".class public " + nome, ".super java/lang/Object", ""]
        for an, at in info["atributos"].items():
            linhas.append(".field public %s %s" % (an, descritor(at)))
        linhas.append("")
        linhas += self._gerar_construtor(decl)
        linhas.append("")
        for m in decl.filhos:
            if m.tipo == "Metodo":
                linhas += self._gerar_metodo(nome, m)
                linhas.append("")
        return "\n".join(linhas) + "\n"

    def _gerar_construtor(self, decl):
        nome = decl.valor
        ctor = next(m for m in decl.filhos if m.tipo == "Construtor")
        params = self._params(ctor.filhos[0])
        self.novo_metodo()
        self.classe_atual = nome
        self.ret_atual = "void"
        self.prox_slot = 1               # slot 0 = this
        self.max_locals = 1
        for tp, nm in params:
            self.declarar_local(nm, tp)
        self.emitir("aload_0")
        self.emitir("invokespecial java/lang/Object/<init>()V")
        # aloca atributos que sao vetores (com suas dimensoes declaradas)
        for m in decl.filhos:
            if m.tipo != "Atributo":
                continue
            at = m.filhos[0].valor
            dims = [c for c in m.filhos if c.tipo == "Dimensao"]
            if at.endswith("[]") and dims:
                self.emitir("aload_0")
                self._gerar_array_alloc(at, [d.filhos[0] for d in dims])
                self.emitir("putfield %s/%s %s" % (nome, m.valor, descritor(at)))
        self._gerar_bloco(ctor.filhos[1], novo_escopo=False)
        self.emitir("return")
        self.classe_atual = None
        descs = "".join(descritor(t) for t, _ in params)
        return [".method public <init>(%s)V" % descs, "    .limit stack 100",
                "    .limit locals %d" % max(self.max_locals, 1)] + self.corpo + [".end method"]

    def _gerar_metodo(self, nome_classe, m):
        ret = m.filhos[0].valor
        params = self._params(m.filhos[1])
        self.novo_metodo()
        self.classe_atual = nome_classe
        self.ret_atual = ret
        self.prox_slot = 1               # slot 0 = this
        self.max_locals = 1
        for tp, nm in params:
            self.declarar_local(nm, tp)
        self._gerar_bloco(m.filhos[2], novo_escopo=False)
        self._retorno_default(ret)
        self.classe_atual = None
        descs = "".join(descritor(t) for t, _ in params)
        return [".method public %s(%s)%s" % (m.valor, descs, descritor(ret)),
                "    .limit stack 100", "    .limit locals %d" % max(self.max_locals, 1)] \
            + self.corpo + [".end method"]

    def _gerar_funcao(self, decl):
        nome = decl.valor
        ret = decl.filhos[0].valor
        params = self._params(decl.filhos[1])
        self.novo_metodo()
        self.ret_atual = ret
        for tp, nm in params:
            self.declarar_local(nm, tp)
        self._gerar_bloco(decl.filhos[2], novo_escopo=False)
        self._retorno_default(ret)
        descs = "".join(descritor(t) for t, _ in params)
        cab = ".method public static %s(%s)%s" % (nome, descs, descritor(ret))
        return ([cab, "    .limit stack 100",
                 "    .limit locals %d" % max(self.max_locals, 1)]
                + self.corpo + [".end method"])

    def _gerar_entrada(self):
        self.novo_metodo()
        self.ret_atual = "void"
        self.prox_slot = 1          # slot 0 = String[] args
        self.max_locals = 1
        # _scanner = new Scanner(System.in)
        self.emitir("new java/util/Scanner")
        self.emitir("dup")
        self.emitir("getstatic java/lang/System/in Ljava/io/InputStream;")
        self.emitir("invokespecial java/util/Scanner/<init>(Ljava/io/InputStream;)V")
        self.emitir("putstatic %s/_scanner Ljava/util/Scanner;" % self.nome_classe)
        # comandos do topo, na ordem
        for item in self.arvore.filhos:
            if item.tipo in ("Funcao", "Classe"):
                continue
            if item.tipo == "Declaracao":
                self._gerar_global_decl(item)
            else:
                self._gerar_comando(item)
        # se existe uma funcao main JSS, chama ela
        if "main" in self.funcoes:
            self.emitir("invokestatic %s/main()V" % self.nome_classe)
        self.emitir("return")
        return (".method public static main([Ljava/lang/String;)V",
                "    .limit stack 100",
                "    .limit locals %d" % max(self.max_locals, 1)) \
            + tuple(self.corpo) + (".end method",)

    def _gerar_global_decl(self, decl):
        tipo = self._tipo_decl(decl)
        dims = [f for f in decl.filhos if f.tipo == "Dimensao"]
        for f in decl.filhos:
            if f.tipo != "Var":
                continue
            init = f.filhos[0] if f.filhos else None
            self._gerar_valor_inicial(tipo, dims, init)
            self.emitir("putstatic %s/%s %s" % (self.nome_classe, f.valor, descritor(tipo)))

    def _retorno_default(self, ret):
        if ret == "void":
            self.emitir("return")
        else:
            self._push_default(ret)
            self.emitir(self._xreturn(ret))

    
    # comandos

    def _gerar_bloco(self, bloco, novo_escopo=True):
        if novo_escopo:
            self.push_escopo()
        for cmd in bloco.filhos:
            self._gerar_comando(cmd)
        if novo_escopo:
            self.pop_escopo()

    def _gerar_comando(self, no):
        t = no.tipo
        if t == "Declaracao":
            self._gerar_decl_local(no)
        elif t == "ExprStmt":
            self._gerar_expr_stmt(no.filhos[0])
        elif t == "If":
            self._gerar_if(no)
        elif t == "While":
            self._gerar_while(no)
        elif t == "For":
            self._gerar_for(no)
        elif t == "Return":
            self._gerar_return(no)
        elif t == "Break":
            self.emitir("goto " + self.breaks[-1])
        elif t == "Bloco":
            self._gerar_bloco(no)
        else:
            raise ErroBackend("comando nao suportado: " + t)

    def _gerar_decl_local(self, decl):
        tipo = self._tipo_decl(decl)
        dims = [f for f in decl.filhos if f.tipo == "Dimensao"]
        for f in decl.filhos:
            if f.tipo != "Var":
                continue
            slot = self.declarar_local(f.valor, tipo)
            init = f.filhos[0] if f.filhos else None
            self._gerar_valor_inicial(tipo, dims, init)
            self._store_slot(slot, tipo)

    def _gerar_valor_inicial(self, tipo, dims, init):
        """Deixa na pilha o valor inicial (array alocado, ou escalar, ou default)."""
        if tipo.endswith("[]"):
            self._gerar_array(tipo, dims, init)
        elif init is not None:
            t = self.gerar_expr(init)
            self._converter(t, tipo)
        else:
            self._push_default(tipo)

    def _gerar_array(self, tipo, dims, init):
        if init is not None and init.tipo == "Vetor" and tipo.count("[]") == 1:
            base = tipo[:-2]
            if dims:
                self.gerar_expr(dims[0].filhos[0])       # tamanho declarado
            else:
                self._push_int(len(init.filhos))
            self._emit_newarray_1d(base)
            for i, elem in enumerate(init.filhos):
                self.emitir("dup")
                self._push_int(i)
                te = self.gerar_expr(elem)
                self._converter(te, base)
                self._emit_arraystore(base)
        elif init is not None and init.tipo != "Vetor":
            self.gerar_expr(init)                        # ja e um array (ex.: outra variavel)
        else:
            self._gerar_array_alloc(tipo, [d.filhos[0] for d in dims])

    def _gerar_array_alloc(self, tipo, dim_exprs):
        for d in dim_exprs:
            self.gerar_expr(d)                           # empilha cada dimensao
        if len(dim_exprs) == 1:
            self._emit_newarray_1d(tipo[:-2])
        else:
            self.emitir("multianewarray %s %d" % (descritor(tipo), len(dim_exprs)))

    def _gerar_vetor_literal(self, no):
        base = no.t[:-2]
        self._push_int(len(no.filhos))
        self._emit_newarray_1d(base)
        for i, elem in enumerate(no.filhos):
            self.emitir("dup")
            self._push_int(i)
            te = self.gerar_expr(elem)
            self._converter(te, base)
            self._emit_arraystore(base)
        return no.t

    def _gerar_indice(self, no):
        base_no, idx_no = no.filhos
        tb = self.gerar_expr(base_no)                    # referencia do array
        self.gerar_expr(idx_no)                          # indice (int)
        elem = tb[:-2]
        self._emit_arrayload(elem)
        return elem

    def _gerar_expr_stmt(self, expr):
        t = self.gerar_expr(expr)
        if t == "void":
            return
        self.emitir("pop2" if t == "real" else "pop")

    def _gerar_if(self, no):
        ramos = no.filhos
        pares = []          # (cond_expr, bloco)
        senao = None
        j = 0
        while j < len(ramos):
            r = ramos[j]
            if r.tipo == "Cond":
                pares.append((r.filhos[0], ramos[j + 1].filhos[0]))
                j += 2
            elif r.tipo == "SenaoSe":
                pares.append((r.filhos[0].filhos[0], r.filhos[1].filhos[0]))
                j += 1
            elif r.tipo == "Senao":
                senao = r.filhos[0]
                j += 1
            else:
                j += 1
        fim = self.rotulo()
        for cond, bloco in pares:
            prox = self.rotulo()
            self.gerar_expr(cond)
            self.emitir("ifeq " + prox)
            self._gerar_bloco(bloco)
            self.emitir("goto " + fim)
            self.marca(prox)
        if senao is not None:
            self._gerar_bloco(senao)
        self.marca(fim)

    def _gerar_while(self, no):
        cond_no, corpo = no.filhos
        ini, fim = self.rotulo(), self.rotulo()
        self.marca(ini)
        self.gerar_expr(cond_no.filhos[0])
        self.emitir("ifeq " + fim)
        self.breaks.append(fim)
        self._gerar_bloco(corpo)
        self.breaks.pop()
        self.emitir("goto " + ini)
        self.marca(fim)

    def _gerar_for(self, no):
        init, cond, upd, corpo = no.filhos
        self.push_escopo()
        for c in init.filhos:
            if c.tipo == "Declaracao":
                self._gerar_decl_local(c)
            else:
                self._gerar_expr_stmt(c)
        ini, fim = self.rotulo(), self.rotulo()
        self.marca(ini)
        for c in cond.filhos:
            self.gerar_expr(c)
            self.emitir("ifeq " + fim)
        self.breaks.append(fim)
        self._gerar_bloco(corpo)
        self.breaks.pop()
        for c in upd.filhos:
            self._gerar_expr_stmt(c)
        self.emitir("goto " + ini)
        self.marca(fim)
        self.pop_escopo()

    def _gerar_return(self, no):
        if no.filhos:
            t = self.gerar_expr(no.filhos[0])
            self._converter(t, self.ret_atual)
            self.emitir(self._xreturn(self.ret_atual))
        else:
            self.emitir("return")

    
    # expressoes (devolvem o tipo JSS do valor deixado na pilha)
    

    def gerar_expr(self, no):
        t = no.tipo
        if t == "Int":
            self._push_int(int(no.valor))
            return "int"
        if t == "Real":
            self._push_double(float(no.valor))
            return "real"
        if t == "Bool":
            self.emitir("iconst_1" if no.valor == "true" else "iconst_0")
            return "bool"
        if t == "Str":
            self.emitir("ldc " + _escapar_str(no.valor[1:-1]))
            return "str"
        if t == "Null":
            self.emitir("aconst_null")
            return no.t
        if t == "Id":
            return self._load_var(no.valor)
        if t == "OpBin":
            return self._gerar_opbin(no)
        if t == "OpUnario":
            return self._gerar_opunario(no)
        if t == "Atrib":
            return self._gerar_atrib(no)
        if t == "Cast":
            return self._gerar_cast(no)
        if t == "Chamada":
            return self._gerar_chamada(no)
        if t == "Indice":
            return self._gerar_indice(no)
        if t == "Vetor":
            return self._gerar_vetor_literal(no)
        if t == "This":
            self.emitir("aload_0")
            return self.classe_atual
        if t == "Membro":
            return self._gerar_membro(no)
        if t == "New":
            return self._gerar_new(no)
        raise ErroBackend("expressao nao suportada: " + t)

    def _gerar_membro(self, no):
        base_no = no.filhos[0]
        attr = no.valor
        tb = self.gerar_expr(base_no)                # referencia do objeto
        at = self.classes[tb]["atributos"][attr]
        self.emitir("getfield %s/%s %s" % (tb, attr, descritor(at)))
        return at

    def _gerar_new(self, no):
        cls = no.valor
        args = no.filhos[0].filhos
        self.emitir("new " + cls)
        self.emitir("dup")
        params = self.classes[cls]["construtor"]
        for (ptipo, _), a in zip(params, args):
            t = self.gerar_expr(a)
            self._converter(t, ptipo)
        descs = "".join(descritor(t) for t, _ in params)
        self.emitir("invokespecial %s/<init>(%s)V" % (cls, descs))
        return cls

    def _gerar_opbin(self, no):
        op = no.valor
        esq, dire = no.filhos
        if op == "+" and no.t == "str":
            return self._gerar_concat(esq, dire)
        if op in ("&&", "||"):
            return self._gerar_logico(no)
        if op in ("==", "!=", "<", "<=", ">", ">="):
            return self._gerar_comparacao(no)
        if op == "**":
            self.gerar_expr(esq); self._para_double(esq.t)
            self.gerar_expr(dire); self._para_double(dire.t)
            self.emitir("invokestatic java/lang/Math/pow(DD)D")
            self.emitir("d2i")
            return "int"
        if no.t == "real":
            self.gerar_expr(esq); self._para_double(esq.t)
            self.gerar_expr(dire); self._para_double(dire.t)
            self.emitir({"+": "dadd", "-": "dsub", "*": "dmul",
                         "/": "ddiv", "%": "drem"}[op])
            return "real"
        self.gerar_expr(esq)
        self.gerar_expr(dire)
        self.emitir({"+": "iadd", "-": "isub", "*": "imul",
                     "/": "idiv", "%": "irem"}[op])
        return "int"

    def _gerar_concat(self, esq, dire):
        self.emitir("new java/lang/StringBuilder")
        self.emitir("dup")
        self.emitir("invokespecial java/lang/StringBuilder/<init>()V")
        te = self.gerar_expr(esq)
        self.emitir("invokevirtual java/lang/StringBuilder/append(%s)Ljava/lang/StringBuilder;"
                    % self._append_desc(te))
        td = self.gerar_expr(dire)
        self.emitir("invokevirtual java/lang/StringBuilder/append(%s)Ljava/lang/StringBuilder;"
                    % self._append_desc(td))
        self.emitir("invokevirtual java/lang/StringBuilder/toString()Ljava/lang/String;")
        return "str"

    def _gerar_logico(self, no):
        op = no.valor
        esq, dire = no.filhos
        if op == "&&":
            falso, fim = self.rotulo(), self.rotulo()
            self.gerar_expr(esq); self.emitir("ifeq " + falso)
            self.gerar_expr(dire); self.emitir("ifeq " + falso)
            self.emitir("iconst_1"); self.emitir("goto " + fim)
            self.marca(falso); self.emitir("iconst_0")
            self.marca(fim)
        else:  # ||
            verd, fim = self.rotulo(), self.rotulo()
            self.gerar_expr(esq); self.emitir("ifne " + verd)
            self.gerar_expr(dire); self.emitir("ifne " + verd)
            self.emitir("iconst_0"); self.emitir("goto " + fim)
            self.marca(verd); self.emitir("iconst_1")
            self.marca(fim)
        return "bool"

    _CMP = {"==": "eq", "!=": "ne", "<": "lt", "<=": "le", ">": "gt", ">=": "ge"}

    def _gerar_comparacao(self, no):
        op = no.valor
        esq, dire = no.filhos
        te, td = esq.t, dire.t
        if te == "str" or td == "str":
            self.gerar_expr(esq)
            self.gerar_expr(dire)
            if op in ("==", "!="):
                self.emitir("invokevirtual java/lang/String/equals(Ljava/lang/Object;)Z")
                if op == "!=":
                    self.emitir("iconst_1"); self.emitir("ixor")
                return "bool"
            self.emitir("invokevirtual java/lang/String/compareTo(Ljava/lang/String;)I")
            return self._bool_de_zero(op)
        if te == "real" or td == "real":
            self.gerar_expr(esq); self._para_double(te)
            self.gerar_expr(dire); self._para_double(td)
            self.emitir("dcmpg")
            return self._bool_de_zero(op)
        # inteiros e booleanos
        self.gerar_expr(esq)
        self.gerar_expr(dire)
        verd, fim = self.rotulo(), self.rotulo()
        self.emitir("if_icmp%s %s" % (self._CMP[op], verd))
        self.emitir("iconst_0"); self.emitir("goto " + fim)
        self.marca(verd); self.emitir("iconst_1")
        self.marca(fim)
        return "bool"

    def _bool_de_zero(self, op):
        # topo da pilha e um int (resultado de dcmpg/compareTo); compara com 0
        verd, fim = self.rotulo(), self.rotulo()
        self.emitir("if%s %s" % (self._CMP[op], verd))
        self.emitir("iconst_0"); self.emitir("goto " + fim)
        self.marca(verd); self.emitir("iconst_1")
        self.marca(fim)
        return "bool"

    def _gerar_opunario(self, no):
        op = no.valor
        operando = no.filhos[0]
        if op == "!":
            self.gerar_expr(operando)
            self.emitir("iconst_1"); self.emitir("ixor")
            return "bool"
        if op == "+":
            return self.gerar_expr(operando)
        if op == "-":
            t = self.gerar_expr(operando)
            self.emitir("dneg" if t == "real" else "ineg")
            return t
        # ++ / -- (pre-fixado) sobre uma variavel
        nome = operando.valor
        t = operando.t
        self._load_var(nome)
        if t == "real":
            self.emitir("dconst_1")
            self.emitir("dadd" if op == "++" else "dsub")
            self.emitir("dup2")
        else:
            self.emitir("iconst_1")
            self.emitir("iadd" if op == "++" else "isub")
            self.emitir("dup")
        self._store_var(nome)
        return t

    def _gerar_atrib(self, no):
        lhs = no.filhos[0]
        if lhs.tipo == "Indice":
            return self._atrib_indice(no)
        if lhs.tipo == "Membro":
            return self._atrib_membro(no)
        _, rhs = no.filhos
        op = no.valor
        nome = lhs.valor
        tvar = lhs.t
        if op == "=":
            t = self.gerar_expr(rhs)
            self._converter(t, tvar)
            self._dup_tipo(tvar)
            self._store_var(nome)
            return tvar
        base = op[:-1]
        if base == "+" and tvar == "str":
            self.emitir("new java/lang/StringBuilder"); self.emitir("dup")
            self.emitir("invokespecial java/lang/StringBuilder/<init>()V")
            self._load_var(nome)
            self.emitir("invokevirtual java/lang/StringBuilder/append(Ljava/lang/String;)Ljava/lang/StringBuilder;")
            t = self.gerar_expr(rhs)
            self.emitir("invokevirtual java/lang/StringBuilder/append(%s)Ljava/lang/StringBuilder;"
                        % self._append_desc(t))
            self.emitir("invokevirtual java/lang/StringBuilder/toString()Ljava/lang/String;")
        elif base in ("&&", "||"):
            self._load_var(nome)
            self.gerar_expr(rhs)
            self.emitir("iand" if base == "&&" else "ior")
        elif tvar == "real":
            self._load_var(nome)
            t = self.gerar_expr(rhs); self._para_double(t)
            self.emitir({"+": "dadd", "-": "dsub", "*": "dmul",
                         "/": "ddiv", "%": "drem"}[base])
        else:
            self._load_var(nome)
            self.gerar_expr(rhs)
            self.emitir({"+": "iadd", "-": "isub", "*": "imul",
                         "/": "idiv", "%": "irem"}[base])
        self._dup_tipo(tvar)
        self._store_var(nome)
        return tvar

    def _atrib_indice(self, no):
        lhs, rhs = no.filhos
        op = no.valor
        base_no, idx_no = lhs.filhos
        elem = lhs.t                        # tipo do elemento (do semantico)
        self.gerar_expr(base_no)            # referencia do array
        self.gerar_expr(idx_no)             # indice
        if op == "=":
            t = self.gerar_expr(rhs)
            self._converter(t, elem)
        else:
            base = op[:-1]
            self.emitir("dup2")             # duplica array+indice para ler o valor atual
            self._emit_arrayload(elem)
            if base == "+" and elem == "str":
                trhs = self.gerar_expr(rhs)
                if trhs != "str":
                    self.emitir("invokestatic java/lang/String/valueOf(%s)Ljava/lang/String;"
                                % self._append_desc(trhs))
                self.emitir("invokevirtual java/lang/String/concat(Ljava/lang/String;)Ljava/lang/String;")
            elif elem == "real":
                trhs = self.gerar_expr(rhs)
                self._para_double(trhs)
                self.emitir({"+": "dadd", "-": "dsub", "*": "dmul",
                             "/": "ddiv", "%": "drem"}[base])
            else:
                self.gerar_expr(rhs)
                self.emitir({"+": "iadd", "-": "isub", "*": "imul",
                             "/": "idiv", "%": "irem"}[base])
        self.emitir("dup2_x2" if elem == "real" else "dup_x2")
        self._emit_arraystore(elem)
        return elem

    def _atrib_membro(self, no):
        lhs, rhs = no.filhos
        op = no.valor
        attr = lhs.valor
        at = lhs.t
        cls = self.gerar_expr(lhs.filhos[0])         # referencia do objeto (= nome da classe)
        if op == "=":
            t = self.gerar_expr(rhs)
            self._converter(t, at)
            self.emitir("dup2_x1" if at == "real" else "dup_x1")
            self.emitir("putfield %s/%s %s" % (cls, attr, descritor(at)))
            return at
        base = op[:-1]
        self.emitir("dup")                           # obj, obj
        self.emitir("getfield %s/%s %s" % (cls, attr, descritor(at)))
        if base == "+" and at == "str":
            trhs = self.gerar_expr(rhs)
            if trhs != "str":
                self.emitir("invokestatic java/lang/String/valueOf(%s)Ljava/lang/String;"
                            % self._append_desc(trhs))
            self.emitir("invokevirtual java/lang/String/concat(Ljava/lang/String;)Ljava/lang/String;")
        elif at == "real":
            trhs = self.gerar_expr(rhs)
            self._para_double(trhs)
            self.emitir({"+": "dadd", "-": "dsub", "*": "dmul",
                         "/": "ddiv", "%": "drem"}[base])
        else:
            self.gerar_expr(rhs)
            self.emitir({"+": "iadd", "-": "isub", "*": "imul",
                         "/": "idiv", "%": "irem"}[base])
        self.emitir("dup2_x1" if at == "real" else "dup_x1")
        self.emitir("putfield %s/%s %s" % (cls, attr, descritor(at)))
        return at

    def _gerar_cast(self, no):
        alvo = no.valor
        arg = no.filhos[0]
        ta = self.gerar_expr(arg)
        if alvo == ta:
            return alvo
        if alvo == "int":
            if ta == "real":
                self.emitir("d2i")
            return "int"
        if alvo == "real":
            if ta in ("int", "bool"):
                self.emitir("i2d")
            return "real"
        if alvo == "bool":
            if ta == "real":
                self.emitir("dconst_0"); self.emitir("dcmpg")
            verd, fim = self.rotulo(), self.rotulo()
            self.emitir("ifne " + verd)
            self.emitir("iconst_0"); self.emitir("goto " + fim)
            self.marca(verd); self.emitir("iconst_1")
            self.marca(fim)
            return "bool"
        if alvo == "str":
            conv = {"int": "I", "real": "D", "bool": "Z"}.get(ta)
            if conv:
                self.emitir("invokestatic java/lang/String/valueOf(%s)Ljava/lang/String;" % conv)
            return "str"
        return alvo

    def _gerar_chamada(self, no):
        callee, args_no = no.filhos
        args = args_no.filhos
        if (callee.tipo == "Membro" and callee.valor == "log"
                and callee.filhos[0].tipo == "Id"
                and callee.filhos[0].valor == "console"
                and self.buscar_local("console") is None
                and "console" not in self.globais):
            return self._gerar_console_log(args)
        if callee.tipo == "Id" and callee.valor == "input":
            return self._gerar_input(args)
        if callee.tipo == "Id" and callee.valor in self.funcoes:
            ret, params = self.funcoes[callee.valor]
            for (ptipo, _), a in zip(params, args):
                t = self.gerar_expr(a)
                self._converter(t, ptipo)
            descs = "".join(descritor(t) for t, _ in params)
            self.emitir("invokestatic %s/%s(%s)%s"
                        % (self.nome_classe, callee.valor, descs, descritor(ret)))
            return ret
        if callee.tipo == "Membro":                  # metodo de objeto: obj.m(args)
            tb = self.gerar_expr(callee.filhos[0])   # referencia do objeto
            ret, params = self.classes[tb]["metodos"][callee.valor]
            for (ptipo, _), a in zip(params, args):
                t = self.gerar_expr(a)
                self._converter(t, ptipo)
            descs = "".join(descritor(t) for t, _ in params)
            self.emitir("invokevirtual %s/%s(%s)%s" % (tb, callee.valor, descs, descritor(ret)))
            return ret
        raise ErroBackend("chamada nao suportada no back-end")

    def _gerar_console_log(self, args):
        for i, a in enumerate(args):
            if i > 0:
                self.emitir("getstatic java/lang/System/out Ljava/io/PrintStream;")
                self.emitir('ldc " "')
                self.emitir("invokevirtual java/io/PrintStream/print(Ljava/lang/String;)V")
            self.emitir("getstatic java/lang/System/out Ljava/io/PrintStream;")
            t = self.gerar_expr(a)
            self.emitir("invokevirtual java/io/PrintStream/print(%s)V" % self._print_desc(t))
        self.emitir("getstatic java/lang/System/out Ljava/io/PrintStream;")
        self.emitir("invokevirtual java/io/PrintStream/println()V")
        return "void"

    def _gerar_input(self, args):
        for a in args:
            if a.tipo != "Id":
                raise ErroBackend("input em vetor/atributo ainda nao suportado")
            tvar = a.t
            self.emitir("getstatic %s/_scanner Ljava/util/Scanner;" % self.nome_classe)
            metodo = {"int": "nextInt()I", "real": "nextDouble()D",
                      "str": "next()Ljava/lang/String;",
                      "bool": "nextBoolean()Z"}[tvar]
            self.emitir("invokevirtual java/util/Scanner/" + metodo)
            self._store_var(a.valor)
        return "void"

    
    # helpers de baixo nivel
    

    def _load_var(self, nome):
        loc = self.buscar_local(nome)
        if loc:
            slot, tipo = loc
            self._load_slot(slot, tipo)
            return tipo
        tipo = self.globais[nome]
        self.emitir("getstatic %s/%s %s" % (self.nome_classe, nome, descritor(tipo)))
        return tipo

    def _store_var(self, nome):
        loc = self.buscar_local(nome)
        if loc:
            slot, tipo = loc
            self._store_slot(slot, tipo)
            return tipo
        tipo = self.globais[nome]
        self.emitir("putstatic %s/%s %s" % (self.nome_classe, nome, descritor(tipo)))
        return tipo

    def _load_slot(self, slot, tipo):
        if tipo == "real":
            self.emitir("dload " + str(slot))
        elif tipo in ("int", "bool"):
            self.emitir("iload " + str(slot))
        else:
            self.emitir("aload " + str(slot))

    def _store_slot(self, slot, tipo):
        if tipo == "real":
            self.emitir("dstore " + str(slot))
        elif tipo in ("int", "bool"):
            self.emitir("istore " + str(slot))
        else:
            self.emitir("astore " + str(slot))

    def _push_int(self, n):
        if -1 <= n <= 5:
            self.emitir("iconst_m1" if n == -1 else "iconst_" + str(n))
        elif -128 <= n <= 127:
            self.emitir("bipush " + str(n))
        elif -32768 <= n <= 32767:
            self.emitir("sipush " + str(n))
        else:
            self.emitir("ldc " + str(n))

    def _push_double(self, x):
        # O ldc2_w do Jasmin le o literal como float (32 bits) e perde precisao;
        # entao carregamos via Double.parseDouble para garantir precisao de double.
        if x == 0.0:
            self.emitir("dconst_0")
        elif x == 1.0:
            self.emitir("dconst_1")
        else:
            self.emitir('ldc "%s"' % repr(x))
            self.emitir("invokestatic java/lang/Double/parseDouble(Ljava/lang/String;)D")

    def _push_default(self, tipo):
        if tipo == "real":
            self.emitir("dconst_0")
        elif tipo in ("int", "bool"):
            self.emitir("iconst_0")
        elif tipo == "str":
            self.emitir('ldc ""')
        else:
            self.emitir("aconst_null")

    def _emit_newarray_1d(self, base):
        if base == "int":
            self.emitir("newarray int")
        elif base == "bool":
            self.emitir("newarray boolean")
        elif base == "real":
            self.emitir("newarray double")
        elif base == "str":
            self.emitir("anewarray java/lang/String")
        else:
            self.emitir("anewarray " + base)     # array de objetos

    def _emit_arraystore(self, elem):
        self.emitir({"int": "iastore", "bool": "bastore",
                     "real": "dastore"}.get(elem, "aastore"))

    def _emit_arrayload(self, elem):
        self.emitir({"int": "iaload", "bool": "baload",
                     "real": "daload"}.get(elem, "aaload"))

    def _converter(self, de, para):
        if de == para:
            return
        if para == "real" and de in ("int", "bool"):
            self.emitir("i2d")

    def _para_double(self, tipo):
        if tipo in ("int", "bool"):
            self.emitir("i2d")

    def _dup_tipo(self, tipo):
        self.emitir("dup2" if tipo == "real" else "dup")

    @staticmethod
    def _xreturn(tipo):
        if tipo == "void":
            return "return"
        if tipo == "real":
            return "dreturn"
        if tipo in ("int", "bool"):
            return "ireturn"
        return "areturn"

    @staticmethod
    def _print_desc(tipo):
        return {"int": "I", "real": "D", "bool": "Z",
                "str": "Ljava/lang/String;"}.get(tipo, "Ljava/lang/Object;")

    @staticmethod
    def _append_desc(tipo):
        return {"int": "I", "real": "D", "bool": "Z",
                "str": "Ljava/lang/String;"}.get(tipo, "Ljava/lang/Object;")


def gerar_jasmin(arvore, nome_classe="Programa"):
    return GeradorJasmin(arvore, nome_classe).gerar()
