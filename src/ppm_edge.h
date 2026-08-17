#ifndef PPM_EDGE_H
#define PPM_EDGE_H

#include <stdint.h>

#define PPM_EDGE_VERSION_MAJOR 0
#define PPM_EDGE_VERSION_MINOR 2
#define PPM_EDGE_VERSION_PATCH 0

typedef enum {
    PPM_PRIORITY_LOW = 0,
    PPM_PRIORITY_NORMAL = 1,
    PPM_PRIORITY_HIGH = 2,
    PPM_PRIORITY_CRITICAL = 3
} ppm_priority_t;

typedef struct {
    int32_t signal;
    int32_t baseline;
    int32_t threshold;
    uint8_t confidence;
    ppm_priority_t priority;
} ppm_input_t;

typedef struct {
    int32_t value;
    uint32_t delta;
    uint8_t protected_mode;
    uint8_t confidence;
    ppm_priority_t priority;
} ppm_output_t;

typedef struct {
    int32_t baseline;
    int32_t last_value;
    int32_t threshold;
    uint8_t initialized;
    uint8_t protection;
    uint8_t confidence;
    ppm_priority_t priority;
} ppm_runtime_t;

void ppm_init(
    ppm_runtime_t *runtime,
    int32_t baseline,
    int32_t threshold
);

void ppm_reset(
    ppm_runtime_t *runtime
);

void ppm_process(
    ppm_runtime_t *runtime,
    const ppm_input_t *input,
    ppm_output_t *output
);

uint32_t ppm_version(void);

#endif
