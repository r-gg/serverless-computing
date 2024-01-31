export class TrainingInfo {
    n_rounds: number;
    n_selected: number;

    constructor(
        n_rounds: number,
        n_selected: number,
    ) {
        this.n_rounds = n_rounds;
        this.n_selected = n_selected;
    }
}