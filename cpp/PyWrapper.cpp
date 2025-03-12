#include "PyWrapper.h"

namespace py {
    GILGuard::GILGuard() {
        gstate = PyGILState_Ensure();
    }

    GILGuard::~GILGuard() {
        PyGILState_Release(gstate);
    }

    Object::Object(PyObject *closure): py_obj(closure) {
        PyGILState_STATE gstate = PyGILState_Ensure();
        Py_XINCREF(closure);
        PyGILState_Release(gstate);
    }

    Object::Object(const Object &other): Object(other.py_obj) {
    }

    Object::Object(Object &&other) noexcept: py_obj(other.py_obj) {
        other.py_obj = nullptr;
    }

    Object::Object(): py_obj(nullptr) {
    }

    Object::~Object() {
        PyGILState_STATE gstate = PyGILState_Ensure();
        Py_XDECREF(py_obj);
        PyGILState_Release(gstate);
    }

    Object &Object::operator=(const Object &other) {
        // Idk if thats correct
        if (this != &other) {
            Object tmp(other);
            *this = std::move(tmp);
        }
        return *this;
    }

    Object &Object::operator=(Object &&other) noexcept {
        if (this != &other) {
            std::swap(py_obj, other.py_obj);
        }
        return *this;
    }

    RefGuard::RefGuard(PyObject *obj): py_obj(obj) {

    }

    RefGuard::RefGuard(const RefGuard &other): py_obj(other.py_obj) {
        if (py_obj) {
            Py_XINCREF(py_obj);
        }
    }

    RefGuard::RefGuard(RefGuard &&other) noexcept: py_obj(other.py_obj) {
        other.py_obj = nullptr;
    }

    RefGuard::~RefGuard() {
        if (py_obj) {
            Py_XDECREF(py_obj);
        }
    }

    RefGuard & RefGuard::operator=(const RefGuard &other) {
        if (this != &other) {
            if (py_obj) {
                Py_XDECREF(py_obj);
            }
            py_obj = other.py_obj;
            if (py_obj) {
                Py_XINCREF(py_obj);
            }
        }
        return *this;
    }

    RefGuard & RefGuard::operator=(RefGuard &&other) noexcept {
        if (this != &other) {
            py_obj = other.py_obj;
            other.py_obj = nullptr;
        }
        return *this;
    }

    void RefGuard::reset() {
        if (py_obj) {
            Py_XDECREF(py_obj);
            py_obj = nullptr;
        }
    }

    PyObject * RefGuard::get() const {
        return py_obj;
    }

    RefGuard::operator struct _object*() const { // NOLINT(*-explicit-constructor)
        return py_obj;
    }

    ErrorGuard::ErrorGuard() {
        py_err = PyErr_GetRaisedException();
    }

    ErrorGuard::~ErrorGuard() {
        restore();
    }

    void ErrorGuard::restore() {
        if (py_err) {
            PyErr_SetRaisedException(py_err);
        }
        py_err = nullptr;
    }

    ErrorGuard & ErrorGuard::operator=(std::nullptr_t) {
        restore();
        return *this;
    }

    void err::raise_exception(PyObject *type, const char *msg, bool set_cause) {
        PyGILState_STATE gstate = PyGILState_Ensure();
        if (PyErr_Occurred()) {
            PyGILState_Release(gstate);
            return;
        }

        PyObject *exc = PyErr_GetRaisedException();

        PyObject *new_exception = PyObject_CallFunction(type, "s", msg);
        PyErr_SetString(new_exception, msg);
        if (exc != nullptr) {
            if (set_cause) {
                PyException_SetCause(new_exception, exc);
            } else {
                PyException_SetContext(new_exception, exc);
            }
        }

        PyErr_SetRaisedException(new_exception);

        PyGILState_Release(gstate);
    }

    void err::raise_exception(PyObject *type, const std::string& msg, bool set_cause) {
        raise_exception(type, msg.c_str(), set_cause);
    }

    void err::raise_runtime_error(const char *msg, bool set_cause) {
        raise_exception(PyExc_RuntimeError, msg, set_cause);
    }

    void err::raise_runtime_error(const std::string &msg, bool set_cause) {
        raise_runtime_error(msg.c_str(), set_cause);
    }

    void err::raise_type_error(const char *msg, bool set_cause) {
        raise_exception(PyExc_TypeError, msg, set_cause);
    }

    void err::raise_type_error(const std::string &msg, bool set_cause) {
        raise_type_error(msg.c_str(), set_cause);
    }
}
