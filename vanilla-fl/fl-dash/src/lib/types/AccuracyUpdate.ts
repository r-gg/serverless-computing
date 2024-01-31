export class AccuracyUpdate {
    accuracy: number;
    round: number;
    accumulated_time: number;

    constructor(
        accuracy: number,
        round: number,
        accumulated_time: number,
    ) {
        this.accuracy = accuracy
        this.round = round
        this.accumulated_time = accumulated_time
    }

    toString(): string {
        return `Accuracy for round ${this.round} in ${this.accumulated_time}: ${this.accuracy}`
    }
}