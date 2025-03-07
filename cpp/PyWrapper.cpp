#include "PyWrapper.h"

namespace py {
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
}
