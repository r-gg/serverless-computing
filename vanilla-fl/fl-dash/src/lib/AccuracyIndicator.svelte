<script lang="ts">
    import {cn} from "$lib/utils";

    export let percentage: number;

    function getProgressColor(percentage: number): string {
        // Interpolate between red (0%) and orange (50%)
        if (percentage <= 25) {
            return "text-red-500"
        } else if (percentage <= 50) {
            return "text-orange-500"
        } else {
            return "text-green-500";
        }
    }

    $: roundedPercentage = Math.floor(percentage * 100);
</script>

<span
    class={cn(getProgressColor(roundedPercentage), "text-lg", "font-bold")}
    style="margin: 0"
>
    {roundedPercentage}%
</span>