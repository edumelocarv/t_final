#!/usr/bin/env python3
"""
jssc -- Compilador da linguagem JSS (Java Script Simplificado).

Front-end (analise):  lexica, sintatica e semantica.
Back-end  (sintese):  gera codigo intermediario JASMIN (JVM) e um executavel.

Uso:
    python3 jssc.py programa.jss            # so analise (front-end)
    python3 jssc.py < programa.jss          # le da entrada padrao
    python3 jssc.py programa.jss --tokens   # tambem mostra os tokens
    python3 jssc.py programa.jss --ast      # tambem mostra a arvore
    python3 jssc.py programa.jss --jvm      # gera build/Programa.class (JASMIN)
    python3 jssc.py programa.jss --run      # gera e EXECUTA o programa

Saida (analise):
    "Compilacao concluida com sucesso." quando o programa e valido;
    "Erro lexico/sintatico/semantico na linha N: ..." quando ha um problema.
"""

import os
import subprocess
import sys

from lexer import tokenizar, ErroLexico
from jss_parser import Parser, ErroSintatico, imprimir_arvore
from semantic import Analisador, ErroSemantico

RAIZ = os.path.dirname(os.path.abspath(__file__))


def ler_codigo(arquivos):
    if arquivos:
        try:
            with open(arquivos[0], "r", encoding="utf-8") as f:
                return f.read()
        except OSError as e:
            print("Nao foi possivel abrir o arquivo: %s" % e)
            sys.exit(2)
    return sys.stdin.read()


def compilar_jvm(arvore, executar):
    """Gera o .j (JASMIN), monta com jasmin.jar e opcionalmente executa."""
    from codegen import gerar_jasmin, ErroBackend
    build = os.path.join(RAIZ, "build")
    os.makedirs(build, exist_ok=True)
    try:
        classes = gerar_jasmin(arvore, "Programa")
    except ErroBackend as e:
        print("Erro no back-end: %s" % e)
        sys.exit(3)

    jasmin = os.path.join(RAIZ, "tools", "jasmin.jar")
    for nome, texto in classes.items():
        caminho_j = os.path.join(build, nome + ".j")
        with open(caminho_j, "w", encoding="utf-8") as f:
            f.write(texto)
        r = subprocess.run(["java", "-jar", jasmin, "-d", build, caminho_j],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print("Erro ao montar com jasmin:\n%s%s" % (r.stdout, r.stderr))
            sys.exit(3)

    print("Gerado: build/Programa.j e build/Programa.class")
    if executar:
        print("----- execucao -----")
        sys.stdout.flush()
        subprocess.run(["java", "-cp", build, "Programa"])


def main():
    args = sys.argv[1:]
    mostrar_tokens = "--tokens" in args
    mostrar_ast = "--ast" in args
    fazer_jvm = "--jvm" in args
    fazer_run = "--run" in args
    arquivos = [a for a in args if not a.startswith("--")]

    codigo = ler_codigo(arquivos)

    try:
        tokens = tokenizar(codigo)
        if mostrar_tokens:
            print("=== TOKENS (analisador lexico) ===")
            for t in tokens:
                print("  linha %3d | %-7s | %r" % (t.linha, t.tipo, t.valor))
            print()

        arvore = Parser(tokens).parse_programa()
        if mostrar_ast:
            print("=== ARVORE SINTATICA (analisador sintatico) ===")
            imprimir_arvore(arvore)
            print()

        Analisador(arvore).analisar()

        if fazer_jvm or fazer_run:
            compilar_jvm(arvore, fazer_run)
        else:
            print("Compilacao concluida com sucesso.")
        sys.exit(0)

    except ErroLexico as e:
        print("Erro lexico na linha %d: %s" % (e.linha, e.mensagem))
        sys.exit(1)
    except ErroSintatico as e:
        print("Erro sintatico na linha %d: %s" % (e.linha, e.mensagem))
        sys.exit(1)
    except ErroSemantico as e:
        print("Erro semantico na linha %d: %s" % (e.linha, e.mensagem))
        sys.exit(1)


if __name__ == "__main__":
    main()
