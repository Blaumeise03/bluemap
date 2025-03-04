#ifndef PYWRAPPER_H
#define PYWRAPPER_H

#include <Python.h>
#include <stdexcept>
#include <iostream>

class PyObjectWrapper {
protected:
    PyObject *py_obj;

public:
    explicit PyObjectWrapper(PyObject *closure);

    PyObjectWrapper(const PyObjectWrapper &other);

    PyObjectWrapper(PyObjectWrapper &&other) noexcept;

    PyObjectWrapper();

    ~PyObjectWrapper();

    PyObjectWrapper &operator=(const PyObjectWrapper &other);

    PyObjectWrapper &operator=(PyObjectWrapper &&other) noexcept;
};

template<typename ReturnType, typename... Args>
class PyClosure : public PyObjectWrapper {
    using PyObjectWrapper::PyObjectWrapper;


    template<typename T>
    void set_arg(PyObject *py_args, int index, T arg) {
        PyObject *py_arg = nullptr;
        if constexpr (std::is_same_v<T, int>) {
            py_arg = PyLong_FromLong(arg);
        } else if constexpr (std::is_same_v<T, double>) {
            py_arg = PyFloat_FromDouble(arg);
        } else if constexpr (std::is_same_v<T, bool>) {
            py_arg = PyBool_FromLong(arg);
        } else if constexpr (std::is_same_v<T, unsigned long long>) {
            py_arg = PyLong_FromUnsignedLongLong(arg);
        } else {
            static_assert(always_false<T>::value, "Unsupported argument type");
        }
        PyTuple_SetItem(py_args, index, py_arg);
    }

    template<typename T, typename... Rest>
    void set_args(PyObject *py_args, int index, T arg, Rest... rest) {
        set_arg(py_args, index, arg);
        set_args(py_args, index + 1, rest...);
    }

    void set_args(PyObject *py_args, int index) {
        // Base case for recursion
    }

    template<typename T>
    struct always_false : std::false_type {
    };

public:
    ReturnType operator()(Args... args) {
        if (!py_obj || !PyCallable_Check(py_obj)) {
            throw std::runtime_error("PyObject is not callable");
        }

        PyObject *py_args = PyTuple_New(sizeof...(Args));
        set_args(py_args, 0, args...);

        PyObject *result = PyObject_CallObject(py_obj, py_args);
        Py_DECREF(py_args);

        if (!result) {
            throw std::runtime_error("Error calling Python function");
        }

        if constexpr (std::is_same_v<ReturnType, int>) {
            if (!PyLong_Check(result)) {
                Py_DECREF(result);
                throw std::runtime_error("Expected an integer return type");
            }
            int value = PyLong_AsLong(result);
            Py_DECREF(result);
            return value;
        } else if constexpr (std::is_same_v<ReturnType, double>) {
            if (!PyFloat_Check(result)) {
                Py_DECREF(result);
                throw std::runtime_error("Expected a double return type");
            }
            double value = PyFloat_AsDouble(result);
            Py_DECREF(result);
            return value;
        } else if constexpr (std::is_same_v<ReturnType, bool>) {
            if (!PyBool_Check(result)) {
                Py_DECREF(result);
                throw std::runtime_error("Expected a boolean return type");
            }
            bool value = PyObject_IsTrue(result);
            Py_DECREF(result);
            return value;
        } else {
            static_assert(always_false<ReturnType>::value, "Unsupported return type");
            return {};
        }
    }

    [[nodiscard]] bool validate() const {
        if (!py_obj || !PyCallable_Check(py_obj)) {
            return false;
        }

        PyObject *callable = nullptr;
        if (PyObject_HasAttrString(py_obj, "__call__")) {
            callable = PyObject_GetAttrString(py_obj, "__call__");
            if (!callable) return false;
        }


        PyObject *code = nullptr;
        if (PyObject_HasAttrString(py_obj, "__code__")) {
            code = PyObject_GetAttrString(py_obj, "__code__");
        } else {
            if (!callable) return false;
            code = PyObject_GetAttrString(callable, "__code__");
        }
        if (!code) return false;


        PyObject *arg_count = PyObject_GetAttrString(code, "co_argcount");
        Py_DECREF(code);
        if (!arg_count) {
            return false;
        }

        int arg_count_int = PyLong_AsLong(arg_count);
        Py_DECREF(arg_count);

        if (callable) {
            if (PyMethod_Check(callable)) {
                arg_count_int -= 1; // Subtract one for the 'self' argument
            }
            Py_DECREF(callable);
        }
        return arg_count_int == sizeof...(Args);
    }
};


#endif //PYWRAPPER_H
