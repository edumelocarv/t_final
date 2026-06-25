#!/usr/bin/env python3
"""
Bateria de conformidade do front-end JSS com a especificacao.

Cada caso tem: descricao, resultado esperado e o codigo-fonte. O esperado e
'ok' (deve compilar) ou um tipo de erro: 'lex', 'sin' ou 'sem'. Para casos de
erro, exigimos apenas que o programa seja recusado na compilacao.

Como rodar (da raiz do projeto):
    python3 tests/conformance.py

Sai com codigo 0 se tudo passar; 1 se houver alguma falha.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lexer import tokenizar, ErroLexico
from jss_parser import Parser, ErroSintatico
from semantic import Analisador, ErroSemantico


def compilar(src):
    try:
        tokens = tokenizar(src)
        arvore = Parser(tokens).parse_programa()
        Analisador(arvore).analisar()
        return ("ok", "")
    except ErroLexico as e:
        return ("lex", e.mensagem)
    except ErroSintatico as e:
        return ("sin", e.mensagem)
    except ErroSemantico as e:
        return ("sem", e.mensagem)
    except Exception as e:                       # bug interno do compilador
        return ("CRASH", repr(e))


CASOS = [
    # ---------- VALIDOS ----------
    ("primitivos -/expoente/escape", "ok",
     'function void main(){ let int a=-5; let real r=-10.8E2; let real q=1e-3; let str s="Ola\\n"; let bool b=true; }'),
    ("const vetor str com lista", "ok",
     'const str[3] nomes=["Ana","Bruno","Carlos"]; function void main(){ console.log(nomes[0]); }'),
    ("vetor: decl, atrib elemento", "ok",
     'function void main(){ let int[3] v; v[0]=1; v[1]=10; v[2]=100; console.log(v[2]); }'),
    ("matriz 2D", "ok",
     'function void main(){ let int[2][2] m; m[0][0]=1; m[1][1]=2; console.log(m[1][1]); }'),
    ("classe completa + objeto + null + const", "ok",
     'class Ponto{ int x; int y; Ponto constructor(int x,int y){ this.x=x; this.y=y; } int soma(){ return this.x+this.y; } } function void main(){ let Ponto p; p=new Ponto(1,2); console.log(p.soma()); p=null; const Ponto q=new Ponto(3,4); }'),
    ("metodo chama metodo via this", "ok",
     'class C{ int a; C constructor(){ this.a=1; } int g(){ return this.a; } int h(){ return this.g()+1; } } function void main(){ let C c=new C(); console.log(c.h()); }'),
    ("objeto como parametro e retorno", "ok",
     'class P{ int x; P constructor(int x){ this.x=x; } } function int lerX(P p){ return p.x; } function P cria(){ return new P(9); } function void main(){ console.log(lerX(cria())); }'),
    ("exemplo de casting da spec 4.5", "ok",
     'function void main(){ let int a; let int b,c,d; input(a); input(b,c,d); console.log("Soma: ",a+b+c+d); console.log(); console.log(int(3.9)); console.log(int(true)); console.log(real(10)); console.log(real(true)); console.log(bool(1)); console.log(bool(0.0)); console.log(str(10+5)); console.log(str(true)); }'),
    ("forward ref entre funcoes", "ok",
     'function void a(){ b(); } function void b(){ console.log("ok"); } function void main(){ a(); }'),
    ("global usa funcao declarada depois", "ok",
     'let int g = f(); function int f(){ return 1; } function void main(){ console.log(g); }'),
    ("funcao usa global declarada depois", "ok",
     'function int f(){ return g; } let int g = 5; function void main(){ console.log(f()); }'),
    ("for com partes vazias", "ok",
     'function void main(){ for(;;){ break; } }'),
    ("bloco anonimo + shadow", "ok",
     'function void main(){ let int x=0; { let int x=1; console.log(x); } console.log(x); }'),
    ("concat str+int e str+bool", "ok",
     'function void main(){ let str s="n="; console.log(s+5); console.log("b="+true); }'),
    ("atribuicao encadeada a=b=c", "ok",
     'function void main(){ let int a; let int b; let int c=3; a=b=c; console.log(a); }'),
    ("** associativo a direita", "ok",
     'function void main(){ console.log(2**3**2); }'),
    ("programa sem main", "ok",
     'let int g=5; function int dobro(int x){ return x*2; }'),
    ("void sem return", "ok",
     'function void f(){ let int x=1; } function void main(){ f(); }'),
    ("compound em real e str", "ok",
     'function void main(){ let real r=1.0; r+=2; let str s="a"; s+="b"; console.log(r); console.log(s); }'),
    ("param sombreia global", "ok",
     'let int x=1; function void f(int x){ console.log(x); } function void main(){ f(2); }'),
    ("underscore id", "ok",
     'function void main(){ let int _x=1; console.log(_x); }'),

    # ---------- ERROS ----------
    ("palavra reservada como id", "sin",
     'function void main(){ let int while=1; }'),
    ("redeclaracao no escopo", "sem",
     'function void main(){ let int x=1; let int x=2; }'),
    ("const reatribuida", "sem",
     'function void main(){ const int N=1; N=2; }'),
    ("vetor const alterado", "sem",
     'function void main(){ const int[3] v=[1,2,3]; v[0]=9; }'),
    ("objeto const alterado", "sem",
     'class P{int x; P constructor(){this.x=0;}} function void main(){ const P p=new P(); p.x=5; }'),
    ("atributo depois de metodo", "sem",
     'class C{ int g(){ return 1; } int x; C constructor(){ this.x=1; } }'),
    ("dois construtores", "sem",
     'class C{ int x; C constructor(){this.x=0;} C constructor(int a){this.x=a;} }'),
    ("classe sem construtor", "sem",
     'class C{ int x; } function void main(){ }'),
    ("variavel nao declarada", "sem",
     'function void main(){ console.log(total); }'),
    ("funcao nao declarada", "sem",
     'function void main(){ foo(); }'),
    ("num de argumentos errado", "sem",
     'function int f(int a){return a;} function void main(){ f(1,2); }'),
    ("tipo de argumento errado", "sem",
     'function int f(int a){return a;} function void main(){ f(true); }'),
    ("retorno incompativel", "sem",
     'function int f(){ return true; }'),
    ("void retorna valor", "sem",
     'function void f(){ return 1; }'),
    ("nao-void sem valor no return", "sem",
     'function int f(){ return; }'),
    ("nao-void sem nenhum return", "sem",
     'function int f(){ let int x=1; }'),
    ("break fora de laco", "sem",
     'function void main(){ break; }'),
    ("cond if nao-bool", "sem",
     'function void main(){ if(5){ } }'),
    ("indice nao-int", "sem",
     'function void main(){ let int[3] v; let int y=v[true]; }'),
    ("indexar nao-vetor", "sem",
     'function void main(){ let int x=1; let int y=x[0]; }'),
    ("comparar vetores com <", "sem",
     'function void main(){ let int[2] a; let int[2] b; let bool x=a<b; }'),
    ("% com reais", "sem",
     'function void main(){ let int x = 5.0 % 2.0; }'),
    ("! em nao-bool", "sem",
     'function void main(){ let bool b = !5; }'),
    ("void usada como valor", "sem",
     'function void f(){} function void main(){ let int x=f(); }'),
    ("input em literal", "sem",
     'function void main(){ input(5); }'),
    ("atributo inexistente", "sem",
     'class P{int x; P constructor(){this.x=0;}} function void main(){ let P p=new P(); console.log(p.z); }'),
    ("metodo inexistente", "sem",
     'class P{int x; P constructor(){this.x=0;}} function void main(){ let P p=new P(); p.nada(); }'),
    ("this fora de classe", "sem",
     'function void main(){ console.log(this); }'),
    ("funcao aninhada", "sin",
     'function void main(){ function void g(){} }'),
    ("init de tipo incompativel", "sem",
     'function void main(){ let bool b=5; }'),
    ("lista atribuida fora da decl", "sem",
     'function void main(){ let int[3] v; v=[1,2,3]; }'),
    ("cast de str para int", "sem",
     'function void main(){ let str s="a"; let int x=int(s); }'),
    ("elementos de vetor de tipos diferentes", "sem",
     'function void main(){ let int[2] v=[1,true]; }'),
]


def main():
    falhas = 0
    for descricao, esperado, src in CASOS:
        categoria, msg = compilar(src)
        if esperado == "ok":
            passou = categoria == "ok"
        else:
            passou = categoria not in ("ok", "CRASH")
        if not passou:
            falhas += 1
        marca = "PASS " if passou else "FALHA"
        extra = "" if categoria == "ok" else f"  [{categoria}] {msg}"
        print(f"{marca} | esperado={esperado:3} | obtido={categoria:5} | {descricao}{extra}")
    print()
    print(f"TOTAL: {len(CASOS)} casos, {falhas} falha(s)")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
