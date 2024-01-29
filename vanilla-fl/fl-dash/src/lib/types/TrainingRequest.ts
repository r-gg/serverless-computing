export class TrainingRequest {
    nRounds: number | null;
    nSelected: number | null;

    constructor(
        nRounds: number | null,
        nSelected: number | null
    ) {
        this.nRounds = nRounds;
        this.nSelected = nSelected;
    }
}