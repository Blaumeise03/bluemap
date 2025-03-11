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


/**
 * A helper macro to trace errors in C++ code and add a Python traceback to the exception. If a c++ exception is raised
 * and no python exception is set, it will raise a new RuntimeError.
 *
 * In any case, the current file, line and function will be added to the traceback for the python exception.
 * Will rethrow the exception afterward.
 *
 * This uses some cheaty hacks which might not work for all future versions of Python.
 *
 * @param code the code to execute (usually a function call)
 */
#define Py_Trace_Errors(code) \
    try { \
        code; \
    } catch (const std::exception &e) { \
        py::ensure_exception(e.what()); \
        py::AddTraceback(__func__, 0, __LINE__, __FILE__); \
        throw e; \
    }


#endif //TRACEBACK_WRAPPER_H
