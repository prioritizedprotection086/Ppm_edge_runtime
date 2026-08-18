/*
 * Minimal CPython C extension exposing the unmodified PPM Edge C kernel
 * (Src/Ppm_edge.c / Src/Ppm_edge.h) directly through the Python C API.
 *
 * PURPOSE: measure the actual CPython <-> C boundary cost for this exact
 * workload, without ctypes.Structure marshalling in the loop. This module
 * #includes Src/Ppm_edge.h unmodified and links Src/Ppm_edge.c unmodified
 * -- it adds zero logic of its own beyond argument unpacking (via the
 * standard PyArg_ParseTuple C API) and return-value packing (via
 * Py_BuildValue). ppm_process() itself is called exactly as written, with
 * no wrapper, no copy of the algorithm, and no behavioral changes.
 *
 * Runtime state (ppm_runtime_t) lives inline in the Python object's memory
 * block (embedded struct, not a separate malloc'd/ctypes-marshalled
 * buffer), so there is no additional indirection beyond what a normal
 * CPython extension type instance already has.
 *
 * Interface is kept as close as practical to the existing ctypes C-kernel
 * baseline (benchmark/baselines/c_kernel.py) for a meaningful comparison:
 *   PPMRuntimeExt(initial_value) -> runtime object
 *   runtime.process(value, threshold, priority) -> (value, delta,
 *       protected_mode: bool, confidence, priority)
 *
 * Does not modify Src/Ppm_edge.c or Src/Ppm_edge.h.
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdint.h>

#include "Ppm_edge.h"

typedef struct {
    PyObject_HEAD
    ppm_runtime_t runtime;
} PPMRuntimeExtObject;

static int
PPMRuntimeExt_init(PPMRuntimeExtObject *self, PyObject *args, PyObject *kwds)
{
    static char *kwlist[] = {"initial_value", NULL};
    int initial_value = 0;

    if (!PyArg_ParseTupleAndKeywords(
            args, kwds, "|i", kwlist, &initial_value)) {
        return -1;
    }

    ppm_init(&self->runtime, (int32_t)initial_value, 0);
    return 0;
}

static PyObject *
PPMRuntimeExt_reset(PPMRuntimeExtObject *self, PyObject *Py_UNUSED(ignored))
{
    ppm_reset(&self->runtime);
    Py_RETURN_NONE;
}

/* Direct call into ppm_process(): PyArg_ParseTuple unpacks the Python
 * ints straight into C stack locals (no intermediate ctypes Structure
 * instances are created), the kernel is called once, and Py_BuildValue
 * packs the C output struct fields straight back into a Python tuple. */
static PyObject *
PPMRuntimeExt_process(PPMRuntimeExtObject *self, PyObject *args)
{
    int32_t value;
    int32_t threshold;
    int priority;

    if (!PyArg_ParseTuple(args, "iii", &value, &threshold, &priority)) {
        return NULL;
    }

    ppm_input_t input;
    ppm_output_t output;

    input.signal = value;
    input.baseline = 0;
    input.threshold = threshold;
    input.confidence = 0;
    input.priority = (ppm_priority_t)priority;

    ppm_process(&self->runtime, &input, &output);

    return Py_BuildValue(
        "iIOii",
        output.value,
        output.delta,
        output.protected_mode ? Py_True : Py_False,
        (int)output.confidence,
        (int)output.priority
    );
}

static PyMethodDef PPMRuntimeExt_methods[] = {
    {"process", (PyCFunction)PPMRuntimeExt_process, METH_VARARGS,
     "process(value, threshold, priority) -> (value, delta, protected_mode, confidence, priority)"},
    {"reset", (PyCFunction)PPMRuntimeExt_reset, METH_NOARGS,
     "reset() -> None"},
    {NULL, NULL, 0, NULL}
};

static PyTypeObject PPMRuntimeExtType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "ppm_edge_ext.PPMRuntimeExt",
    .tp_basicsize = sizeof(PPMRuntimeExtObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_doc = PyDoc_STR("CPython extension wrapper around the C PPM kernel (ppm_process)."),
    .tp_methods = PPMRuntimeExt_methods,
    .tp_init = (initproc)PPMRuntimeExt_init,
    .tp_new = PyType_GenericNew,
};

static PyModuleDef ppm_edge_ext_module = {
    PyModuleDef_HEAD_INIT,
    .m_name = "ppm_edge_ext",
    .m_doc = "Minimal CPython C-extension boundary around the unmodified PPM C kernel.",
    .m_size = -1,
};

PyMODINIT_FUNC
PyInit_ppm_edge_ext(void)
{
    PyObject *m;

    if (PyType_Ready(&PPMRuntimeExtType) < 0) {
        return NULL;
    }

    m = PyModule_Create(&ppm_edge_ext_module);
    if (m == NULL) {
        return NULL;
    }

    Py_INCREF(&PPMRuntimeExtType);
    if (PyModule_AddObject(m, "PPMRuntimeExt", (PyObject *)&PPMRuntimeExtType) < 0) {
        Py_DECREF(&PPMRuntimeExtType);
        Py_DECREF(m);
        return NULL;
    }

    return m;
}
