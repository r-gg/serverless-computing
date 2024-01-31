<script lang="ts">
    import {Card, CardHeader, CardTitle} from "$lib/components/ui/card/index.js";
    import type {ClientUpdate} from "$lib/types/ClientUpdate";
    import AccuracyIndicator from "$lib/AccuracyIndicator.svelte";

    export let clientUpdate: ClientUpdate;
</script>

<Card>
  <CardHeader class="flex flex-row justify-between items-center p-2">
    <CardTitle class="w-fit">
      Client {clientUpdate.client_id}
      <span class="ml-2 text-primary/50">took {clientUpdate.time}s</span>
    </CardTitle>
    <AccuracyIndicator percentage={clientUpdate.accuracy}/>
  </CardHeader>
</Card>