#include <stdio.h>

#include "ppm_edge.h"

int main(void)
{
    ppm_runtime_t runtime;

    ppm_init(
        &runtime,
        500,
        100
    );

    ppm_input_t input = {
        .signal = 520,
        .baseline = 500,
        .threshold = 100,
        .confidence = 100,
        .priority = PPM_PRIORITY_NORMAL
    };

    ppm_output_t output;

    ppm_process(
        &runtime,
        &input,
        &output
    );

    printf("PPM Edge Runtime\n");
    printf("Version: %u.%u.%u\n",
           PPM_EDGE_VERSION_MAJOR,
           PPM_EDGE_VERSION_MINOR,
           PPM_EDGE_VERSION_PATCH);

    printf("Signal: %u\n", output.value);
    printf("Delta: %u\n", output.delta);
    printf("Protection: %u\n", output.protected_mode);
    printf("Confidence: %u\n", output.confidence);
    printf("Priority: %u\n", output.priority);

    return 0;
}
