#include "traceback_wrapper.h"

#include <iostream>
#include <PyWrapper.h>

namespace py {
    std::unordered_map<int, PyObject *> global_code_object_cache;

    inline PyObject *global_code_object_cache_find(int line) {
        if (const auto it = global_code_object_cache.find(line); it != global_code_object_cache.end()) {
            const auto co = it->second;
            Py_INCREF(co);
            return co;
        }
        return nullptr;
    }

    inline void global_code_object_cache_insert(int line, PyObject *code_object) {
        Py_INCREF(code_object);
        global_code_object_cache[line] = code_object;
    }

    PyObject *PyCode_Replace_For_AddTraceback(PyObject *code, PyObject *scratch_dict,
                                              PyObject *firstlineno, PyObject *name) {
        if (PyDict_SetItemString(scratch_dict, "co_firstlineno", firstlineno)) return nullptr;
        if (PyDict_SetItemString(scratch_dict, "co_name", name)) return nullptr;

        if (const RefGuard replace = PyObject_GetAttrString(code, "replace")) {
            const RefGuard empty_tuple = PyTuple_New(0);
            PyObject *result = PyObject_Call(replace, empty_tuple, scratch_dict);
            return result;
        }
        PyErr_Clear();
        return nullptr;
    }

    void AddTraceback(const char *funcname, int c_line, int py_line, const char *filename) {
        GILGuard gil_guard;
        if (!PyErr_Occurred()) {
            return;
        }
        RefGuard dict = nullptr;
        ErrorGuard error_guard;

        RefGuard code_object = global_code_object_cache_find(c_line ? -c_line : py_line);
        if (!code_object) {
            code_object = Py_CompileString("_getframe()", filename, Py_eval_input);
            if (!code_object) return;
            RefGuard py_py_line = PyLong_FromLong(py_line);
            if (!py_py_line) return;
            RefGuard py_funcname = PyUnicode_FromString(funcname);
            if (!py_funcname) return;
            dict = PyDict_New();
            if (!dict) return; {
                RefGuard old_code_object = code_object;
                code_object = PyCode_Replace_For_AddTraceback(code_object, dict, py_py_line, py_funcname);
            }
            if (!code_object) return;
            global_code_object_cache_insert(c_line ? -c_line : py_line, code_object);
        } else {
            dict = PyDict_New();
        }
        // getframe is borrowed
        PyObject *getframe = PySys_GetObject("_getframe");
        if (!getframe) return;

        if (PyDict_SetItemString(dict, "_getframe", getframe)) return;
        const RefGuard frame = PyEval_EvalCode(code_object, dict, dict);
        if (!frame || frame == Py_None) return;

        error_guard.restore();
        PyTraceBack_Here(reinterpret_cast<_frame *>(frame.get()));
    }

    void ensure_exception(const char *msg) {
        PyGILState_STATE gstate = PyGILState_Ensure();
        if (PyErr_Occurred()) {
            PyGILState_Release(gstate);
            return;
        }

        err::raise_runtime_error(msg);
    }
}
