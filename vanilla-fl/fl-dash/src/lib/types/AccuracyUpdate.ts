export class AccuracyUpdate {
    accuracy: number;
    roundNr: number;
    nModels: number;

    constructor(
        accuracy: number,
        roundNr: number,
        nModels: number,
    ) {
        this.accuracy = accuracy
        this.roundNr = roundNr
        this.nModels = nModels
    }

    toString(): string {
        return `Accuracy for round ${this.roundNr} using ${this.nModels} clients: ${this.accuracy}`
    }
}