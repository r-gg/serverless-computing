<script lang="ts">
    import {Button} from "$lib/components/ui/button";
    import {Input} from "$lib/components/ui/input";
    import {Card, CardContent, CardHeader, CardTitle} from "$lib/components/ui/card/index.js";
    import ioClient, {Socket} from "socket.io-client"
    import {Badge} from "$lib/components/ui/badge";
    import {AccuracyUpdate} from "$lib/types/AccuracyUpdate";
    import {Client} from "$lib/types/Client";
    import {TrainingInfo} from "$lib/types/TrainingInfo";
    import {Toaster} from "$lib/components/ui/sonner";
    import {toast} from "svelte-sonner";
    import {TrainingRequest} from "$lib/types/TrainingRequest";

    import {Line} from 'svelte-chartjs'
    import {
        CategoryScale,
        Chart as ChartJS,
        Legend,
        LinearScale,
        LineElement,
        PointElement,
        Title,
        Tooltip,
    } from 'chart.js';

    ChartJS.register(
        Title,
        Tooltip,
        Legend,
        LineElement,
        LinearScale,
        PointElement,
        CategoryScale
    );
    // TODO: extract Accuracy Chart components
    // TODO: extract state into store
    // TODO: extract WebsocketConnection into store
    // TODO: extract WebsocketCreationForm into Component
    // TODO: extract TrainingForm into component
    // TODO: handle all training round updates in their own component
    // TODO: create custom component for client cards
    // TODO: create custom component for update cards

    let url: string = '';
    let accuracy: AccuracyUpdate[] = [];
    let clients: Client[] = [];
    let currentTraining: TrainingInfo | null = null;
    let trainingRequest: TrainingRequest = new TrainingRequest(null, null);
    let socket: Socket | null = null;
    let connectionIsPending: boolean = false;
    let isConnected: boolean = false;
    let chartRef: any;
    let accuracyData = {
        labels: [],
        datasets: [{
            label: "Current training",
            borderColor: '#f97316',
            data: []
        }]
    }

    function connect(): void {
        if (!url) {
            toast.error("Error has occurred")
            return;
        }

        try {
            connectionIsPending = true
            socket = ioClient(url)
            socket.connect()
            fetch("http://127.0.0.1:8080/get_clients")
                .then(res => res.json())
                .then(data => clients = data)
                .catch(error => console.error(error))
            connectionIsPending = false
        } catch (error: any) {
            console.error(error)
            toast.error("Error has occurred", {
                description: error.message
            })
            return;
        }

        socket.on("update_accuracy", (event: { data: AccuracyUpdate }) => {
            console.log(event)
            accuracy.push(event.data)
            accuracy = accuracy
            addDataToChart(chartRef, accuracy.length, event.data.accuracy)
        });

        socket.on("training_started", (event: { data: TrainingInfo }) => {
            console.log(event)
            currentTraining = event.data
        });

        socket.on("client_registered", (event: { data: Client }) => {
            console.log(event)
            clients.push(event.data)
            clients = clients
        });

        socket.on("connect", () => {
            console.log("connected")
            isConnected = socket?.connected || true
        });

        socket.on("disconnect", (reason) => {
            console.log("disconnected")
            isConnected = socket?.connected || false
        });

        socket.on("connect_error", (socket) => {
            console.error(socket)
            toast.error("Error has occurred")
        });
    }

    function addDataToChart(chart: any, label: string, newData: number) {
        chart?.data.labels.push(label);
        chart?.data.datasets.forEach((dataset) => {
            dataset.data.push(newData);
        });
        chart?.update();
    }

    function startTraining() {
        socket?.emit("start_training", trainingRequest.nRounds, trainingRequest.nSelected)
    }

    function disconnect() {
        socket?.removeAllListeners()
        socket?.disconnect()
    }

    function clear() {
        trainingRequest = new TrainingRequest(0, 0)
        currentTraining = null
        accuracy = []
    }
</script>

<main class="min-h-screen min-w-full flex items-center flex-col gap-3 p-4">
  <div class="w-full flex justify-center gap-4">
    <Card class="w-[40%] h-fit">
      <CardHeader class="flex justify-between relative">
        <CardTitle>Connect to FL Backend</CardTitle>
        <Badge class="absolute right-6 top-4">
          {#if isConnected && (url !== null || url !== undefined)}
            Connected to {url}
          {:else}
            Disconnected
          {/if}
        </Badge>
      </CardHeader>
      <CardContent>
        <div class="flex flex-col gap-2 items-end">
          <Input
              type="text"
              bind:value={url}
              placeholder="Enter WebSocket URL"
          />
          {#if !isConnected}
            <Button
                on:click={connect}
                disabled={!url || isConnected || connectionIsPending}
            >
              Connect
            </Button>
          {:else}
            <Button
                on:click={disconnect}
                disabled={connectionIsPending}
            >
              Disconnect
            </Button>
          {/if}
        </div>
      </CardContent>
    </Card>
    {#if url !== null && isConnected}
      <Card class="w-[40%] h-fit">
        <CardHeader class="flex justify-between">
          <CardTitle>Start Training</CardTitle>
        </CardHeader>
        <CardContent>
          <div class="flex flex-col gap-2">
            <div class="flex gap-2">
              <Input
                  type="number"
                  bind:value={trainingRequest.nRounds}
                  placeholder="Number of training rounds"
                  min="0"
              />
              <Input
                  type="number"
                  bind:value={trainingRequest.nSelected}
                  placeholder="Necessary Models"
                  min="0" max={clients.length}
              />
            </div>
            <div class="flex gap-2">
              <Button on:click={clear}>
                Clear
              </Button>
              <Button
                  class="ml-auto"
                  on:click={startTraining}
                  disabled={
                  trainingRequest.nSelected == null || trainingRequest.nRounds == null ||
                  trainingRequest.nSelected <= 0 || trainingRequest.nRounds <= 0
              }>
                Start
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    {/if}
  </div>

  <div class="flex gap-4 w-full">
    <div class="w-full flex justify-center gap-4">
      {#if isConnected}
        <div class="flex gap-4 w-1/3">
          {#if currentTraining}
            <Card class="flex flex-col gap-3 w-full">
              <CardHeader class="relative">
                <CardTitle>Updates</CardTitle>
                <Badge class="absolute top-4 right-6">
                  {accuracy.length}
                </Badge>
              </CardHeader>
              <CardContent class="flex flex-col gap-2">
                {#each accuracy as accuracyUpdate}
                  <Card>
                    {`Accuracy for round ${accuracyUpdate.roundNr} using ${accuracyUpdate.nModels} clients: ${accuracyUpdate.accuracy}`}
                  </Card>
                {/each}
              </CardContent>
            </Card>
          {/if}
        </div>
        <div class="flex w-2/3 gap-4 items-start justify-end">
          {#if currentTraining}
            <Card class="w-1/2 h-fit">
              <CardHeader>
                <CardTitle>Accuracy</CardTitle>
              </CardHeader>
              <CardContent class="flex flex-col gap-2">
                <Line
                    data={accuracyData}
                    options="{{responsive: true}}"
                    bind:chart={chartRef}
                />
              </CardContent>
            </Card>
          {/if}
          <Card class="w-1/2 h-fit">
            <CardHeader>
              <CardTitle>Clients</CardTitle>
            </CardHeader>
            <CardContent class="flex flex-col gap-2">
              {#if clients.length === 0}
                There are currently 0 connected clients
              {:else}
                {#each clients as client}
                  <Card>
                    {`Client ${client.client_id} on port ${client.port}`}
                  </Card>
                {/each}
              {/if}
            </CardContent>
          </Card>
        </div>
      {/if}
    </div>
  </div>

  <Toaster/>
</main>