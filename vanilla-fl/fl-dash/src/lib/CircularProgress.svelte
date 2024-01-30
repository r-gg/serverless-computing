<script>
    import resolveConfig from 'tailwindcss/resolveConfig'
    import tailwindConfig from '../../tailwind.config.js'

    const fullConfig = resolveConfig(tailwindConfig)
    console.log(fullConfig.theme)
    export let percentage = 0; // Percentage value
    export let size = 100; // Size of the circle
    export let strokeWidth = 10; // Width of the stroke
    //TODO: Fix this baseColor to work with themes
    export let baseColor = "#ddd"; // Color of the base circle

    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const progress = circumference - (percentage / 100) * circumference;

    // Function to interpolate color based on percentage
    function getProgressColor(percentage) {
        // Interpolate between red (0%) and orange (50%)
        if (percentage <= 50) {
            const r = 255;
            const g = Math.round(128 + (percentage / 50) * (255 - 128));
            return `rgb(${r}, ${g}, 0)`;
        }
        // Interpolate between orange (50%) and green (100%)
        const r = Math.round(255 - ((percentage - 50) / 50) * 255);
        const g = 255;
        return `rgb(${r}, ${g}, 0)`;
    }

    // Calculated color based on percentage
    $: progressColor = getProgressColor(percentage);
</script>

<svg width={size} height={size}>
    <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={baseColor}
            stroke-width={strokeWidth}
    />
    <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={progressColor}
            stroke-width={strokeWidth}
            stroke-dasharray={`${circumference} ${circumference}`}
            stroke-dashoffset={progress}
            transform={`rotate(-90 ${size / 2} ${size / 2})`}
    />
    <text
            x="50%"
            y="50%"
            dominant-baseline="middle"
            text-anchor="middle"
            font-size="20px"
    >
        {percentage}%
    </text>
</svg>

<style>
    circle {
        transition: stroke-dashoffset 0.3s, stroke 0.3s;
    }
</style>
