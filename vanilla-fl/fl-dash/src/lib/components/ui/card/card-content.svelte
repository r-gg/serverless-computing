<script lang="ts">
	import { cn } from "$lib/utils";
	import type { HTMLAttributes } from "svelte/elements";

	type $$Props = HTMLAttributes<HTMLDivElement>;

	let ref: HTMLDivElement;
	let className: $$Props["class"] = undefined;
	export { className as class, ref as ref };
</script>

<div class={cn("p-6 pt-0", className)} bind:this={ref} {...$$restProps}>
	<slot />
</div>
