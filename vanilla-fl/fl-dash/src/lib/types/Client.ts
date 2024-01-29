export class Client {
    client_id: number;
    port: number;

    constructor(
        client_id: number,
        port: number,
    ) {
        this.client_id = client_id
        this.port = port
    }

    toString(): string {
        return `Client ${this.client_id} on port ${this.port}`
    }
}