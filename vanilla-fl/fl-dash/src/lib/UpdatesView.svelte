<script lang="ts">
    import {Card, CardContent, CardHeader, CardTitle} from "$lib/components/ui/card";
    import {Badge} from "$lib/components/ui/badge";
    import {AccuracyUpdate} from "$lib/types/AccuracyUpdate";
    import {ClientUpdate} from "$lib/types/ClientUpdate";
    import {TrainingInfo} from "$lib/types/TrainingInfo";
    import ClientUpdateCard from "$lib/components/ui/ClientUpdateCard.svelte";
    import {CardFooter} from "$lib/components/ui/card/index.js";
    import AccuracyIndicator from "$lib/AccuracyIndicator.svelte";
    import {afterUpdate} from "svelte";
    import LoadingSpinner from "$lib/components/ui/LoadingSpinner.svelte";

    export let currentTraining: TrainingInfo;
    export let data: AccuracyUpdate[] = [];
    $: if (data) {
        if (currentTraining.n_rounds === data.length) clientUpdatesPerRound = clientUpdatesPerRound
    }
    export let clientUpdatesPerRound: Map<number, ClientUpdate[]> = new Map<number, ClientUpdate[]>();
    let cardListRef: HTMLDivElement;

    function isDataAvailableForRound(round: number) {
        return round - 1 < data.length;
    }

    afterUpdate(() => {
        if (cardListRef) scrollToBottom(cardListRef)
    });

    async function scrollToBottom(node: HTMLDivElement) {
        node.scroll({top: node.scrollHeight, behavior: 'smooth'});
    }
</script>

<Card class="flex flex-col gap-3 w-full max-h-full">
  <CardHeader class="relative">
    <CardTitle>Updates</CardTitle>
    <Badge class="absolute top-4 right-6">
      {data.length} / {currentTraining.n_rounds}
    </Badge>
  </CardHeader>
  <CardContent class="p-0 overflow-auto">
    <div
        class="p-6 pt-0 flex flex-col gap-3 max-h-full overflow-auto transition-all"
        bind:this={cardListRef}
    >
      {#each clientUpdatesPerRound.entries() as [round, clientUpdates] (round)}
        {#if clientUpdates}
          <Card class="overflow-clip">
            <CardHeader class="p-2.5">
              <CardTitle>Round {round}</CardTitle>
            </CardHeader>
            <CardContent class="flex flex-col gap-2 p-2.5 pt-0">
              {#each clientUpdates as clientUpdate}
                {#if clientUpdate.client_id !== undefined}
                  <ClientUpdateCard clientUpdate={clientUpdate}/>
                {/if}
              {/each}
            </CardContent>
            <CardFooter class="py-2.5 px-5 bg-gray-200 dark:bg-slate-900">
              <div class="w-full flex flex-row justify-between items-center gap-2">
                <h3 class="text-lg font-semibold leading-none tracking-tight w-fit">Test Accuracy</h3>
                {#if isDataAvailableForRound(round)}
                  <AccuracyIndicator percentage={data[round - 1].accuracy}/>
                {:else}
                  <LoadingSpinner class="h-5 w-5"/>
                {/if}
              </div>
            </CardFooter>
          </Card>
        {/if}
      {/each}
    </div>
  </CardContent>
</Card>