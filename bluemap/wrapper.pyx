# distutils: language = c++
cdef extern from "functions.h":
    int add(int a, int b)

def py_add(int a, int b):
    return add(a, b)