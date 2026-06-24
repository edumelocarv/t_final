// Exemplo VALIDO 4: classes, objetos, construtor, metodos, this e new.

class Ponto {
    int x;
    int y;

    Ponto constructor(int x, int y) {
        this.x = x;
        this.y = y;
    }

    int soma() {
        return this.x + this.y;
    }
}

function void main() {
    let Ponto p1;
    p1 = new Ponto(1, 2);
    console.log("Soma de p1:", p1.soma());
    console.log("x de p1:", p1.x);
    p1 = null;                       // um objeto pode receber null

    const Ponto p2 = new Ponto(10, 100);
    console.log("Soma de p2:", p2.soma());
}
