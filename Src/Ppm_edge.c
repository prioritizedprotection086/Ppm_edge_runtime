#include "ppm_edge.h"

static uint16_t absolute_delta(
    uint16_t a,
    uint16_t b
) {
    return (a > b) ? (a - b) : (b - a);
}

void ppm_init(
    ppm_runtime_t *runtime,
    uint16_t baseline,
    uint16_t threshold
) {
    if (runtime == 0) {
        return;
    }

    runtime->baseline = baseline;
    runtime->last_value = baseline;
    runtime->threshold = threshold;

    runtime->initialized = 1;
    runtime->protection = 0;
    runtime->confidence = 0;
    runtime->priority = PPM_PRIORITY_NORMAL;
}

void ppm_reset(
    ppm_runtime_t *runtime
) {
    if (runtime == 0) {
        return;
    }

    runtime->last_value = runtime->baseline;
    runtime->protection = 0;
    runtime->confidence = 0;
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

    if (!runtime->initialized) {
        ppm_init(
            runtime,
            input->baseline,
            input->threshold
        );
    }

    uint16_t delta =
        absolute_delta(input->signal, runtime->last_value);

    uint8_t protected_mode = 0;

    /*
     * Protection is activated when the signal exceeds
     * the supplied threshold or when the caller explicitly
     * marks the event as critical.
     */
    if (delta >= input->threshold ||
        input->priority == PPM_PRIORITY_CRITICAL) {
        protected_mode = 1;
    }

    /*
     * Confidence is intentionally bounded.
     *
     * This is a deterministic placeholder for the adaptive
     * policy layer. More sophisticated policy can be added
     * without changing the public runtime interface.
     */
    uint8_t confidence;

    if (delta == 0) {
        confidence = 100;
    } else if (delta < input->threshold) {
        confidence = 75;
    } else {
        confidence = 50;
    }

    runtime->last_value = input->signal;
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
