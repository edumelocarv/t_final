#!/usr/bin/env python3
"""
jssc -- Compilador da linguagem JSS (Java Script Simplificado).
Front-end (etapa de analise): analise lexica e sintatica.

Uso:
    python3 jssc.py programa.jss            # le de um arquivo
    python3 jssc.py < programa.jss          # le da entrada padrao
    python3 jssc.py programa.jss --tokens   # tambem mostra os tokens (lexer)
    python3 jssc.py programa.jss --ast      # tambem mostra a arvore (parser)

Saida:
    "Compilacao concluida com sucesso." quando o programa e valido;
    "Erro lexico/sintatico na linha N: ..." quando ha algum problema.
"""

import sys

from lexer import tokenizar, ErroLexico
from jss_parser import Parser, ErroSintatico, imprimir_arvore


def ler_codigo(arquivos):
    """Le o programa de um arquivo (se informado) ou da entrada padrao."""
    if arquivos:
        caminho = arquivos[0]
        try:
            with open(caminho, "r", encoding="utf-8") as f:
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
        # 1) Analise lexica: texto -> lista de tokens
        tokens = tokenizar(codigo)
        if mostrar_tokens:
            print("=== TOKENS (saida do analisador lexico) ===")
            for t in tokens:
                print(f"  linha {t.linha:>3} | {t.tipo:<7} | {t.valor!r}")
            print()

        # 2) Analise sintatica: tokens -> arvore sintatica
        arvore = Parser(tokens).parse_programa()
        if mostrar_ast:
            print("=== ARVORE SINTATICA (saida do analisador sintatico) ===")
            imprimir_arvore(arvore)
            print()

        print("Compilacao concluida com sucesso.")
        sys.exit(0)

    except ErroLexico as e:
        print(f"Erro lexico na linha {e.linha}: {e.mensagem}")
        sys.exit(1)
    except ErroSintatico as e:
        print(f"Erro sintatico na linha {e.linha}: {e.mensagem}")
        sys.exit(1)


if __name__ == "__main__":
    main()
