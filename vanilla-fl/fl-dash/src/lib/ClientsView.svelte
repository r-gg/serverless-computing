<script lang="ts">
    import {Card, CardContent, CardHeader, CardTitle} from "$lib/components/ui/card/index.js";
    import {Client} from "$lib/types/Client";

    export let clients: Client[];
</script>

<Card>
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