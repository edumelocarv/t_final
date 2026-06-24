#!/usr/bin/env python3
"""
jssc -- Compilador da linguagem JSS (Java Script Simplificado).
Front-end completo: analise lexica, sintatica e semantica.

Uso:
    python3 jssc.py programa.jss            # le de um arquivo
    python3 jssc.py < programa.jss          # le da entrada padrao
    python3 jssc.py programa.jss --tokens   # tambem mostra os tokens (lexer)
    python3 jssc.py programa.jss --ast      # tambem mostra a arvore (parser)

Saida:
    "Compilacao concluida com sucesso." quando o programa e valido;
    "Erro lexico/sintatico/semantico na linha N: ..." quando ha algum problema.
"""

import sys

from lexer import tokenizar, ErroLexico
from jss_parser import Parser, ErroSintatico, imprimir_arvore
from semantic import Analisador, ErroSemantico


def ler_codigo(arquivos):
    if arquivos:
        try:
            with open(arquivos[0], "r", encoding="utf-8") as f:
                return f.read()
        except OSError as e:
            print(f"Nao foi possivel abrir o arquivo: {e}")
            sys.exit(2)
    return sys.stdin.read()


def main():
    args = sys.argv[1:]
    mostrar_tokens = "--tokens" in args
    mostrar_ast = "--ast" in args
    arquivos = [a for a in args if not a.startswith("--")]

    codigo = ler_codigo(arquivos)

    try:
        # 1) analise lexica: texto -> tokens
        tokens = tokenizar(codigo)
        if mostrar_tokens:
            print("=== TOKENS (analisador lexico) ===")
            for t in tokens:
                print(f"  linha {t.linha:>3} | {t.tipo:<7} | {t.valor!r}")
            print()

        # 2) analise sintatica: tokens -> arvore sintatica
        arvore = Parser(tokens).parse_programa()
        if mostrar_ast:
            print("=== ARVORE SINTATICA (analisador sintatico) ===")
            imprimir_arvore(arvore)
            print()

        # 3) analise semantica: verifica tipos, escopos, etc.
        Analisador(arvore).analisar()

        print("Compilacao concluida com sucesso.")
        sys.exit(0)

    except ErroLexico as e:
        print(f"Erro lexico na linha {e.linha}: {e.mensagem}")
        sys.exit(1)
    except ErroSintatico as e:
        print(f"Erro sintatico na linha {e.linha}: {e.mensagem}")
        sys.exit(1)
    except ErroSemantico as e:
        print(f"Erro semantico na linha {e.linha}: {e.mensagem}")
        sys.exit(1)


if __name__ == "__main__":
    main()
