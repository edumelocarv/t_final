// Exemplo VALIDO 1: fatorial com recursao, if/else, chamada de funcao.

function int fatorial(int n) {
    if (n > 1) {
        return n * fatorial(n - 1);
    } else {
        return 1;
    }
}

function void main() {
    let int numero;
    console.log("Digite um numero:");
    input(numero);
    console.log("Fatorial:", fatorial(numero));
}
