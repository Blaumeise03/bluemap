#ifndef TRACEBACK_WRAPPER_H
#define TRACEBACK_WRAPPER_H

#include <Python.h>
#include <stdexcept>
#include <unordered_map>


namespace py {
    extern std::unordered_map<int, PyObject *> global_code_object_cache;

    void AddTraceback(const char *funcname, int c_line,
                      int py_line, const char *filename);

    struct trace_error final : std::runtime_error {
        using std::runtime_error::runtime_error;
    };

    void ensure_exception(const char *msg);
}


#define Py_Trace_Errors(code) \
    try { \
        code; \
    } catch (const std::exception &e) { \
        py::ensure_exception(e.what()); \
        py::AddTraceback(__func__, 0, __LINE__, __FILE__); \
        throw e; \
    }


#endif //TRACEBACK_WRAPPER_H
