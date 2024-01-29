<script lang="ts">
    import {Card, CardContent, CardHeader, CardTitle} from "$lib/components/ui/card";
    import {Badge} from "$lib/components/ui/badge";
    import type {AccuracyUpdate} from "$lib/types/AccuracyUpdate";

    export let data: AccuracyUpdate[];
</script>

<Card class="flex flex-col gap-3 w-full max-h-full">
  <CardHeader class="relative">
    <CardTitle>Updates</CardTitle>
    <Badge class="absolute top-4 right-6">
      {data.length}
    </Badge>
  </CardHeader>
  <CardContent class="flex flex-col gap-2 max-h-full scroll-auto">
    {#each data as update}
      <Card>
        {`Accuracy for round ${update.roundNr} using ${update.nModels} clients: ${update.accuracy}`}
      </Card>
    {/each}
  </CardContent>
</Card>