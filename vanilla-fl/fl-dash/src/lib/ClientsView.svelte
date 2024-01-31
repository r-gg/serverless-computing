<script lang="ts">
    import {Card, CardContent, CardHeader, CardTitle} from "$lib/components/ui/card/index.js";
    import {Client} from "$lib/types/Client";
    import ClientCard from "$lib/components/ClientCard.svelte";

    export let clients: Client[];
</script>

<Card>
  <CardHeader>
    <CardTitle>Clients</CardTitle>
  </CardHeader>
  <CardContent class="flex flex-wrap gap-2">
    {#if clients.length === 0}
      There are currently 0 connected clients
    {:else}
      {#each clients as client}
        <ClientCard client={client}/>
      {/each}
    {/if}
  </CardContent>
</Card>