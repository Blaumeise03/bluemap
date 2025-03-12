#ifndef PYWRAPPER_H
#define PYWRAPPER_H

#include <Python.h>
#include <stdexcept>
#include <iostream>


namespace py {
    class GILGuard {
        PyGILState_STATE gstate;

    public:
        GILGuard();

        ~GILGuard();
    };

    class Object {
    protected:
        PyObject *py_obj;

    public:
        explicit Object(PyObject *closure);

        Object(const Object &other);

        Object(Object &&other) noexcept;

        Object();

        ~Object();

        Object &operator=(const Object &other);

        Object &operator=(Object &&other) noexcept;
    };

    /**
     * A guard for strong references to Python objects. Will decrement the reference count when it goes out of scope.
     *
     * IT DOES NOT INCREMENT THE REFERENCE COUNT WHEN CONSTRUCTED. Only use this if you already own a reference to the
     * object.
     */
    class RefGuard {
    public:
        RefGuard(PyObject *obj = nullptr);

        /// Copy constructor
        RefGuard(const RefGuard &other);

        /// Move constructor
        RefGuard(RefGuard &&other) noexcept;

        /// Destructor
        ~RefGuard();

        /// Copy assignment operator
        RefGuard &operator=(const RefGuard &other);

        /// Move assignment operator
        RefGuard &operator=(RefGuard &&other) noexcept;

        /// Explicitly delete the reference
        void reset();

        /// Access the underlying PyObject
        [[nodiscard]] PyObject *get() const;

        /// Allow implicit conversion to PyObject*
        operator PyObject *() const;

    private:
        PyObject *py_obj = nullptr;
    };

    /**
     * Ensures that there is no exception set in Python. It will collect the exception and set it again once it gets
     * destroyed.
     */
    class ErrorGuard {
        PyObject *py_err;

    public:
        ErrorGuard();

        ~ErrorGuard();

        void restore();

        ErrorGuard& operator=(std::nullptr_t);
    };

    namespace err {
        /// Raise a Python exception with the given message. If set_cause is true, the current exception will be set as
        /// the cause, otherwise it will be set as the context.
        void raise_exception(PyObject* type, const char *msg, bool set_cause = false);
        void raise_exception(PyObject *type, const std::string& msg, bool set_cause = false);

        void raise_runtime_error(const char *msg, bool set_cause = false);
        void raise_runtime_error(const std::string& msg, bool set_cause = false);

        void raise_type_error(const char *msg, bool set_cause = false);
        void raise_type_error(const std::string& msg, bool set_cause = false);
    }

    template<typename ReturnType, typename... Args>
    class Callable : public Object {
        using Object::Object;

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
        /**
         * Call the Python function with the given arguments. Will aquire the GIL and release it after the call.
         * @param args
         * @return
         */
        ReturnType operator()(Args... args) {
            PyGILState_STATE gstate = PyGILState_Ensure();

            if (!py_obj || !PyCallable_Check(py_obj)) {
                PyGILState_Release(gstate);
                throw std::runtime_error("PyObject is not callable");
            }

            PyObject *py_args = PyTuple_New(sizeof...(Args));
            set_args(py_args, 0, args...);

            PyObject *result = PyObject_CallObject(py_obj, py_args);
            Py_DECREF(py_args);

            if (!result) {
                PyObject *exc = PyErr_GetRaisedException();

                PyObject *new_exception = PyObject_CallFunction(PyExc_RuntimeError, "s",
                                                                "Error calling Python function");
                PyErr_SetString(new_exception, "Error calling Python function");
                PyException_SetCause(new_exception, exc);

                PyErr_SetRaisedException(new_exception);

                PyGILState_Release(gstate);
                throw std::runtime_error("Error calling Python function");
            }

            if constexpr (std::is_same_v<ReturnType, int>) {
                if (!PyLong_Check(result)) {
                    Py_DECREF(result);
                    PyGILState_Release(gstate);
                    throw std::runtime_error("Expected an integer return type");
                }
                int value = PyLong_AsLong(result);
                Py_DECREF(result);
                PyGILState_Release(gstate);
                return value;
            } else if constexpr (std::is_same_v<ReturnType, double>) {
                if (!PyFloat_Check(result)) {
                    Py_DECREF(result);
                    PyGILState_Release(gstate);
                    throw std::runtime_error("Expected a double return type");
                }
                double value = PyFloat_AsDouble(result);
                Py_DECREF(result);
                PyGILState_Release(gstate);
                return value;
            } else if constexpr (std::is_same_v<ReturnType, bool>) {
                if (!PyBool_Check(result)) {
                    Py_DECREF(result);
                    PyGILState_Release(gstate);
                    throw std::runtime_error("Expected a boolean return type");
                }
                bool value = PyObject_IsTrue(result);
                Py_DECREF(result);
                PyGILState_Release(gstate);
                return value;
            } else if constexpr (std::is_same_v<ReturnType, std::tuple<int, int, int>>) {
                if (!PyTuple_Check(result) || PyTuple_Size(result) != 3) {
                    Py_DECREF(result);
                    PyGILState_Release(gstate);
                    throw std::runtime_error("Expected a tuple return type");
                }
                int x = PyLong_AsLong(PyTuple_GetItem(result, 0));
                int y = PyLong_AsLong(PyTuple_GetItem(result, 1));
                int z = PyLong_AsLong(PyTuple_GetItem(result, 2));
                Py_DECREF(result);
                PyGILState_Release(gstate);
                return {x, y, z};
            } else {
                static_assert(always_false<ReturnType>::value, "Unsupported return type");
                PyGILState_Release(gstate);
                return {};
            }
        }

        [[nodiscard]] bool validate() const {
            PyGILState_STATE gstate = PyGILState_Ensure();
            if (!py_obj || !PyCallable_Check(py_obj)) {
                err::raise_type_error("Python object is not callable");
                PyGILState_Release(gstate);
                return false;
            }

            PyObject *callable = nullptr;
            if (PyObject_HasAttrString(py_obj, "__call__")) {
                callable = PyObject_GetAttrString(py_obj, "__call__");
                if (!callable) {
                    err::raise_type_error("Python object is not callable (error while getting __call__ attribute)", true);
                    PyGILState_Release(gstate);
                    return false;
                }
            }

            PyObject *code = nullptr;
            if (PyObject_HasAttrString(py_obj, "__code__")) {
                code = PyObject_GetAttrString(py_obj, "__code__");
                Py_DECREF(callable);
                callable = nullptr;
            } else {
                if (!callable) {
                    err::raise_type_error("Python object is not callable (does not have __code__ attribute and no __call__ attribute)");
                    PyGILState_Release(gstate);
                    return false;
                }
                code = PyObject_GetAttrString(callable, "__code__");
            }
            if (!code) {
                err::raise_type_error("Did not find code object in callable object");
                PyGILState_Release(gstate);
                return false;
            }

            PyObject *arg_count = PyObject_GetAttrString(code, "co_argcount");
            Py_DECREF(code);
            if (!arg_count) {
                err::raise_runtime_error("Failed to get argument count from code object");
                PyGILState_Release(gstate);
                return false;
            }

            int arg_count_int = PyLong_AsLong(arg_count);
            Py_DECREF(arg_count);

            if (callable) {
                if (PyMethod_Check(callable)) {
                    arg_count_int -= 1; // Subtract one for the 'self' argument
                }
                Py_DECREF(callable);
            } else {
                if (PyMethod_Check(py_obj)) {
                    arg_count_int -= 1;
                }
            }
            const bool arg_cnt_ok = arg_count_int == sizeof...(Args);
            if (!arg_cnt_ok) {
                err::raise_type_error("Argument count mismatch, expected " + std::to_string(sizeof...(Args)) +
                                      " but got " + std::to_string(arg_count_int));
            }
            PyGILState_Release(gstate);
            return arg_cnt_ok;
        }
    };
}

#endif //PYWRAPPER_H
