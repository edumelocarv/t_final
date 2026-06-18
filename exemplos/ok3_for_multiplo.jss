// Exemplo VALIDO 3: laco 'for' com varias atribuicoes separadas por virgula,
// no init e no update (conforme a especificacao v2).

function void main() {
    let int i;
    let int j;
    for (i = 0, j = 10; i < j; ++i, --j) {
        console.log(i, j);
    }
}
