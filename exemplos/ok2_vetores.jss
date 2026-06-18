// Exemplo VALIDO 2: vetores, laco for e while, operadores e conversao de tipo.

const int[3] notas = [8, 6, 10];
let real media = 0.0;

function real somaVetor(int[] v, int tam) {
    let real soma = 0.0;
    for (let int i = 0; i < tam; ++i) {
        soma += v[i];
    }
    return soma;
}

function void main() {
    let int total = 0;
    let int i = 0;
    while (i < 3) {
        total += notas[i];
        ++i;
    }
    media = real(total) / 3.0;
    console.log("Media:", media);

    let bool aprovado = media >= 7.0 && total > 0;
    console.log("Aprovado:", aprovado);
}
