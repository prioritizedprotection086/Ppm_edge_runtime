#include "Ppm_edge.h"

static uint32_t absolute_delta(
    int32_t a,
    int32_t b
) {
    int64_t difference = (int64_t)a - (int64_t)b;

    if (difference < 0) {
        difference = -difference;
    }

    if (difference > UINT32_MAX) {
        return UINT32_MAX;
    }

    return (uint32_t)difference;
}

static uint8_t calculate_confidence(
    uint32_t delta,
    uint32_t threshold
) {
    if (delta == 0U) {
        return 100U;
    }

    if (delta < threshold) {
        return 75U;
    }

    return 50U;
}

void ppm_init(
    ppm_runtime_t *runtime,
    int32_t baseline,
    int32_t threshold
) {
    if (runtime == 0) {
        return;
    }

    if (threshold < 0) {
        threshold = 0;
    }

    runtime->baseline = baseline;
    runtime->last_value = baseline;
    runtime->threshold = threshold;

    runtime->initialized = 0U;
    runtime->protection = 0U;
    runtime->confidence = 0U;
    runtime->priority = PPM_PRIORITY_NORMAL;
}

void ppm_reset(
    ppm_runtime_t *runtime
) {
    if (runtime == 0) {
        return;
    }

    runtime->last_value = runtime->baseline;
    runtime->initialized = 0U;
    runtime->protection = 0U;
    runtime->confidence = 0U;
    runtime->priority = PPM_PRIORITY_NORMAL;
}

void ppm_process(
    ppm_runtime_t *runtime,
    const ppm_input_t *input,
    ppm_output_t *output
) {
    if (runtime == 0 || input == 0 || output == 0) {
        return;
    }

    int32_t threshold_value = input->threshold;

    if (threshold_value < 0) {
        threshold_value = 0;
    }

    uint32_t threshold = (uint32_t)threshold_value;

    uint32_t delta = absolute_delta(
        input->signal,
        runtime->last_value
    );

    uint8_t protected_mode = 0U;

    if (delta >= threshold ||
        input->priority == PPM_PRIORITY_CRITICAL) {
        protected_mode = 1U;
    }

    uint8_t confidence = calculate_confidence(
        delta,
        threshold
    );

    runtime->last_value = input->signal;
    runtime->threshold = threshold_value;
    runtime->initialized = 1U;
    runtime->protection = protected_mode;
    runtime->confidence = confidence;
    runtime->priority = input->priority;

    output->value = input->signal;
    output->delta = delta;
    output->protected_mode = protected_mode;
    output->confidence = confidence;
    output->priority = input->priority;
}

uint32_t ppm_version(void)
{
    return
        ((uint32_t)PPM_EDGE_VERSION_MAJOR << 16) |
        ((uint32_t)PPM_EDGE_VERSION_MINOR << 8) |
        ((uint32_t)PPM_EDGE_VERSION_PATCH);
}
