<script lang="ts">
    import {Card, CardHeader, CardTitle} from "$lib/components/ui/card";
    import type {Client} from "$lib/types/Client";

    export let client: Client;
</script>

<Card class="flex-1 min-w-[150px]">
  <CardHeader class="w-fit p-2.5">
    <CardTitle class="w-fit">Client {client.client_id}</CardTitle>
    <span class="text-primary/50 font-thin" style="margin: 0">Port {client.port}</span>
  </CardHeader>
</Card>