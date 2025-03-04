#include "PyWrapper.h"

PyObjectWrapper::PyObjectWrapper(PyObject *closure): py_obj(closure) {
    PyGILState_STATE gstate = PyGILState_Ensure();
    Py_XINCREF(closure);
    PyGILState_Release(gstate);
}

PyObjectWrapper::PyObjectWrapper(const PyObjectWrapper &other): PyObjectWrapper(other.py_obj) {
}

PyObjectWrapper::PyObjectWrapper(PyObjectWrapper &&other) noexcept: py_obj(other.py_obj) {
    other.py_obj = nullptr;
}

PyObjectWrapper::PyObjectWrapper(): py_obj(nullptr) {
}

PyObjectWrapper::~PyObjectWrapper() {
    PyGILState_STATE gstate = PyGILState_Ensure();
    Py_XDECREF(py_obj);
    PyGILState_Release(gstate);
}

PyObjectWrapper & PyObjectWrapper::operator=(const PyObjectWrapper &other) {
    // Idk if thats correct
    if (this != &other) {
        PyObjectWrapper tmp(other);
        *this = std::move(tmp);
    }
    return *this;
}

PyObjectWrapper & PyObjectWrapper::operator=(PyObjectWrapper &&other) noexcept {
    if (this != &other) {
        std::swap(py_obj, other.py_obj);
    }
    return *this;
}
