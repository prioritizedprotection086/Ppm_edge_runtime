#include <stdio.h>
#include <stdint.h>
#include <limits.h>
#include "Ppm_edge.h"

static void one(ppm_runtime_t *rt, int32_t sig, int32_t th, ppm_priority_t pr) {
    ppm_input_t in = { .signal = sig, .baseline = 0, .threshold = th, .confidence = 100, .priority = pr };
    ppm_output_t out;
    ppm_process(rt, &in, &out);
    printf("ROW %d %u %u %u %u\n", out.value, (unsigned)out.delta, (unsigned)out.protected_mode, (unsigned)out.confidence, (unsigned)out.priority);
}

int main(void) {
    ppm_runtime_t rt;
    printf("SUITE threshold\n");
    ppm_init(&rt, 0, 10); one(&rt, 0, 10, PPM_PRIORITY_NORMAL); one(&rt, 9, 10, PPM_PRIORITY_NORMAL);
    ppm_init(&rt, 0, 10); one(&rt, 0, 10, PPM_PRIORITY_NORMAL); one(&rt, 10, 10, PPM_PRIORITY_NORMAL);
    ppm_init(&rt, 0, 10); one(&rt, 0, 10, PPM_PRIORITY_NORMAL); one(&rt, 11, 10, PPM_PRIORITY_NORMAL);
    printf("SUITE zero_delta\n");
    ppm_init(&rt, 0, 10); one(&rt, 42, 10, PPM_PRIORITY_NORMAL); one(&rt, 42, 10, PPM_PRIORITY_NORMAL);
    printf("SUITE pos_neg\n");
    ppm_init(&rt, 0, 15); one(&rt, 100, 15, PPM_PRIORITY_NORMAL); one(&rt, 90, 15, PPM_PRIORITY_NORMAL); one(&rt, 110, 15, PPM_PRIORITY_NORMAL);
    printf("SUITE int32\n");
    ppm_init(&rt, 0, 1); one(&rt, 0, 1, PPM_PRIORITY_NORMAL); one(&rt, INT32_MAX, 1, PPM_PRIORITY_NORMAL);
    ppm_init(&rt, 0, 1); one(&rt, 0, 1, PPM_PRIORITY_NORMAL); one(&rt, INT32_MIN, 1, PPM_PRIORITY_NORMAL);
    ppm_init(&rt, 0, 1); one(&rt, INT32_MIN, 1, PPM_PRIORITY_NORMAL); one(&rt, INT32_MAX, 1, PPM_PRIORITY_NORMAL);
    printf("SUITE critical\n");
    ppm_init(&rt, 0, 100); one(&rt, 0, 100, PPM_PRIORITY_NORMAL); one(&rt, 1, 100, PPM_PRIORITY_CRITICAL);
    printf("SUITE neg_threshold\n");
    ppm_init(&rt, 0, -5); one(&rt, 0, -5, PPM_PRIORITY_NORMAL); one(&rt, 1, -5, PPM_PRIORITY_NORMAL);
    printf("SUITE reset\n");
    ppm_init(&rt, 0, 10); one(&rt, 50, 10, PPM_PRIORITY_NORMAL); ppm_reset(&rt); one(&rt, 5, 10, PPM_PRIORITY_NORMAL);
    printf("SUITE repeated\n");
    ppm_init(&rt, 0, 1); for (int i = 0; i < 20; i++) one(&rt, 7, 1, PPM_PRIORITY_NORMAL);
    printf("DONE\n");
    return 0;
}
