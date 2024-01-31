export class ClientUpdate {
    client_id: number;
    round: number;
    accuracy: number;
    time: number;

    constructor(
        client_id: number,
        accuracy: number,
        round: number,
        time: number,
    ) {
        this.client_id = client_id
        this.accuracy = accuracy
        this.round = round
        this.time = time
    }

    toString(): string {
        return `Accuracy for round ${this.round} in ${this.time}: ${this.accuracy}`
    }
}