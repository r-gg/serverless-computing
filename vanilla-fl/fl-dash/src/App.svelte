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
    import UpdatesView from "$lib/UpdatesView.svelte";
    import ClientsView from "$lib/ClientsView.svelte";
    import type {ClientUpdate} from "$lib/types/ClientUpdate";
    import {ModeWatcher} from "mode-watcher";
    import ThemeToggle from "$lib/components/ThemeToggle.svelte";

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

    let url: string = '';
    let accuracy: AccuracyUpdate[] = [];
    let clients: Client[] = [];
    let currentTraining: TrainingInfo | null = null;
    let trainingRequest: TrainingRequest = new TrainingRequest(null, null);
    let socket: Socket | null = null;
    let connectionIsPending: boolean = false;
    let isConnected: boolean = false;
    let chartRef: any;
    let accuracyData = initAccuracyData()
    let clientUpdatesPerRound: Map<number, ClientUpdate[]> = initClientUpdatesPerRound();

    function connect(): void {
        if (!url) {
            toast.error("Error has occurred")
            return;
        }

        try {
            connectionIsPending = true
            socket = ioClient(url)
            socket.connect()
            getClients()
            connectionIsPending = false
        } catch (error: any) {
            console.error(error)
            toast.error("Error has occurred", {
                description: error.message
            })
            return;
        }

        socket.on("update_accuracy", (event: { data: AccuracyUpdate }) => {
            console.log(event.data)
            accuracy = [...accuracy, event.data];
            addDataToChart(chartRef, accuracy.length, event.data.accuracy)
        });

        socket.on("update_client", (event: { data: ClientUpdate }) => {
            const clientUpdate = event.data
            console.log(clientUpdate)
            const round = clientUpdate.round
            if (clientUpdatesPerRound.has(round)) {
                clientUpdatesPerRound.get(round)?.push(
                    clientUpdate
                )
            } else {
                clientUpdatesPerRound.set(round, [clientUpdate])
            }
            clientUpdatesPerRound = clientUpdatesPerRound
        })

        socket.on("training_started", (event: { data: TrainingInfo }) => {
            console.log(event.data)
            currentTraining = event.data
        });

        socket.on("client_registered", (event: { data: Client }) => {
            console.log(event.data)
            clients.push(event.data)
            clients = clients
        });

        socket.on("connect", () => {
            isConnected = socket?.connected || true
            console.log("connected")
        });

        socket.on("disconnect", () => {
            isConnected = socket?.connected || false
            console.log("disconnected")
        });

        socket.on("connect_error", (socket) => {
            console.error(socket)
            toast.error("Error has occurred")
        });
    }

    function getClients() {
        fetch("http://127.0.0.1:8080/get_clients")
            .then(res => res.json())
            .then(data => clients = data)
            .catch(error => console.error(error))
    }

    function addDataToChart(chart: any, label: number, newData: number) {
        chart?.data.labels.push(`${label}`);
        chart?.data.datasets.forEach((dataset) => {
            dataset.data.push(newData);
        });
        chart?.update();
    }

    function initAccuracyData() {
        return {
            labels: [],
            datasets: [{
                label: "Current training",
                borderColor: '#f97316',
                data: []
            }]
        }
    }

    function initClientUpdatesPerRound() {
        return new Map<number, ClientUpdate[]>()
    }

    function startTraining() {
        currentTraining = null
        accuracy = []
        accuracyData = initAccuracyData()
        clientUpdatesPerRound = initClientUpdatesPerRound()
        socket?.emit("start_training", trainingRequest.nRounds, trainingRequest.nSelected)
        if (clients.length <= 0) getClients()
    }

    function disconnect() {
        console.log("Disconnect")
        socket?.removeAllListeners()
        socket?.disconnect()
        socket = null;
        isConnected = false
        clear();
    }

    function clear() {
        trainingRequest = new TrainingRequest(0, 0)
        currentTraining = null
        accuracy = []
        accuracyData = initAccuracyData()
        clientUpdatesPerRound = initClientUpdatesPerRound()
    }
</script>

<main class="h-screen w-screen flex items-center flex-col gap-3 pt-4 px-4 pb-6">
  <ThemeToggle
      class="absolute top-4 right-4"
  />

  <div class="w-full flex justify-center gap-4 max-h-full">
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
      <div class="w-[40%] h-fit">
        <Card>
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
      </div>
    {/if}
  </div>

  <div class="w-full max-h-full flex justify-center gap-4 overflow-auto">
    {#if isConnected}
      <div class="flex gap-4 w-1/2 max-h-full overflow-auto">
        {#if currentTraining}
          <UpdatesView
              currentTraining={currentTraining}
              data={accuracy}
              clientUpdatesPerRound={clientUpdatesPerRound}
          />
        {/if}
      </div>
      <div class="flex flex-col w-1/2 gap-4 max-h-full overflow-auto">
        <div class="h-fit">
          <ClientsView clients={clients}/>
        </div>
        {#if currentTraining}
          <Card class="max-h-full overflow-auto">
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
      </div>
    {/if}
  </div>

  <Toaster/>
  <ModeWatcher/>
</main>