"""
Analisador Lexico (Lexer) da linguagem JSS (Java Script Simplificado).

O lexer le o codigo-fonte (texto puro) e o transforma em uma lista de TOKENS.
Um token e a menor unidade com significado da linguagem: uma palavra-chave,
um numero, um nome (identificador), um operador, etc. Cada token guarda tambem
a LINHA em que apareceu, para podermos indicar onde ocorreu um erro.
"""


# Conjuntos de palavras que o lexer precisa reconhecer

# Palavras reservadas: nao podem ser usadas como nome de variavel/funcao.
PALAVRAS_RESERVADAS = {
    "function", "void", "let", "const", "if", "else", "while", "for",
    "break", "return", "class", "constructor", "new", "this",
}

# Tipos da linguagem. Tambem funcionam como funcoes de conversao: int(x), real(x)...
TIPOS = {"int", "real", "str", "bool"}

# Operadores e pontuacao. ORDEM IMPORTA: os mais longos vem primeiro para que
# "==" seja reconhecido antes de "=", "**" antes de "*", e assim por diante.
OPERADORES = [
    # 3 caracteres
    "**=", "&&=", "||=",
    # 2 caracteres
    "==", "!=", ">=", "<=", "&&", "||", "++", "--", "**",
    "+=", "-=", "*=", "/=", "%=",
    # 1 caractere
    "+", "-", "*", "/", "%", "=", ">", "<", "!",
    "(", ")", "{", "}", "[", "]", ";", ",", ".",
]


class Token:
    """Uma peca do programa, com sua categoria (tipo), texto (valor) e a linha."""

    def __init__(self, tipo, valor, linha):
        self.tipo = tipo      # categoria: "ID", "INT", "REAL", "STR", "BOOL",
        self.valor = valor    #            "NULL", "PALAVRA", "TIPO", "OP", "EOF"
        self.linha = linha

    def __repr__(self):
        return f"Token({self.tipo!r}, {self.valor!r}, linha={self.linha})"


class ErroLexico(Exception):
    """Erro encontrado durante a analise lexica (ex.: caractere invalido)."""

    def __init__(self, linha, mensagem):
        self.linha = linha
        self.mensagem = mensagem
        super().__init__(f"Erro lexico na linha {linha}: {mensagem}")


# Funcao principal do lexer
def tokenizar(codigo):
    """Recebe o codigo-fonte (string) e devolve a lista de tokens."""
    tokens = []
    i = 0                 # posicao atual no texto
    linha = 1             # linha atual (para mensagens de erro)
    n = len(codigo)

    while i < n:
        c = codigo[i]

        # 1) Quebra de linha -> apenas conta a linha.
        if c == "\n":
            linha += 1
            i += 1
            continue

        # 2) Espacos em branco -> ignora.
        if c in " \t\r":
            i += 1
            continue

        # 3) Comentario de linha: // ... ate o fim da linha.
        if c == "/" and i + 1 < n and codigo[i + 1] == "/":
            while i < n and codigo[i] != "\n":
                i += 1
            continue

        # 4) String entre aspas duplas: "..."
        if c == '"':
            valor, i = _ler_string(codigo, i, linha)
            tokens.append(Token("STR", valor, linha))
            continue

        # 5) Numero (inteiro ou real).
        if c.isdigit():
            valor, tipo, i = _ler_numero(codigo, i)
            tokens.append(Token(tipo, valor, linha))
            continue

        # 6) Identificador ou palavra reservada (comeca com letra ou '_').
        if c.isalpha() or c == "_":
            j = i
            while j < n and (codigo[j].isalnum() or codigo[j] == "_"):
                j += 1
            palavra = codigo[i:j]
            i = j
            tokens.append(Token(_classificar_palavra(palavra), palavra, linha))
            continue

        # 7) Operadores e pontuacao.
        op = _casar_operador(codigo, i)
        if op is not None:
            tokens.append(Token("OP", op, linha))
            i += len(op)
            continue

        # 8) Nenhuma regra casou -> caractere invalido na linguagem.
        raise ErroLexico(linha, f"caractere invalido {c!r}")

    # Token especial que marca o fim do arquivo (facilita o trabalho do parser).
    tokens.append(Token("EOF", "", linha))
    return tokens


# Auxiliares

def _classificar_palavra(palavra):
    """Decide a categoria de uma sequencia de letras/digitos/underscore."""
    if palavra in PALAVRAS_RESERVADAS:
        return "PALAVRA"
    if palavra in TIPOS:
        return "TIPO"
    if palavra in ("true", "false"):
        return "BOOL"
    if palavra == "null":
        return "NULL"
    return "ID"


def _ler_string(codigo, i, linha):
    """Le uma string a partir da aspa inicial. Devolve (texto, nova_posicao)."""
    n = len(codigo)
    i += 1  # pula a aspa de abertura
    partes = []
    # sequencias de escape suportadas: \n, \t, \", \\, \r, \0
    escapes = {"n": "\n", "t": "\t", '"': '"', "\\": "\\", "r": "\r", "0": "\0"}
    while i < n:
        c = codigo[i]
        if c == '"':
            return "".join(partes), i + 1   # pula a aspa de fechamento
        if c == "\n":
            raise ErroLexico(linha, "string nao fechada (faltou aspas)")
        if c == "\\":
            if i + 1 >= n:
                raise ErroLexico(linha, "string nao fechada (faltou aspas)")
            prox = codigo[i + 1]
            partes.append(escapes.get(prox, prox))
            i += 2
            continue
        partes.append(c)
        i += 1
    raise ErroLexico(linha, "string nao fechada (faltou aspas)")


def _ler_numero(codigo, i):
    """Le um numero. Devolve (texto, 'INT' ou 'REAL', nova_posicao)."""
    n = len(codigo)
    inicio = i
    eh_real = False

    while i < n and codigo[i].isdigit():
        i += 1

    # Parte decimal: um '.' SEGUIDO de digito (ex.: 1.5). Senao, o '.' fica
    # para o proximo token (ex.: em "p1.x" o ponto e acesso a atributo).
    if i < n and codigo[i] == "." and i + 1 < n and codigo[i + 1].isdigit():
        eh_real = True
        i += 1
        while i < n and codigo[i].isdigit():
            i += 1

    # Expoente: E/e com sinal opcional, ex.: 10.8E2, 1e-3.
    if i < n and codigo[i] in "eE":
        j = i + 1
        if j < n and codigo[j] in "+-":
            j += 1
        if j < n and codigo[j].isdigit():
            eh_real = True
            i = j
            while i < n and codigo[i].isdigit():
                i += 1

    texto = codigo[inicio:i]
    return texto, ("REAL" if eh_real else "INT"), i


def _casar_operador(codigo, i):
    """Tenta casar um operador a partir da posicao i (o mais longo primeiro)."""
    for op in OPERADORES:
        if codigo.startswith(op, i):
            return op
    return None
