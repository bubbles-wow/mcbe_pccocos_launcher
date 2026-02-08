#define PY_SSIZE_T_CLEAN
#include <windows.h>
#include "Python.h"

#include <iostream>

std::string GetExeDir() {
    char buffer[MAX_PATH];
    GetModuleFileNameA(NULL, buffer, MAX_PATH);
    std::string path(buffer);
    return path.substr(0, path.find_last_of("\\/"));
}

std::string GetPythonError() {
    PyObject* type, * value, * traceback;
    PyErr_Fetch(&type, &value, &traceback);
    PyErr_NormalizeException(&type, &value, &traceback);

    if (value == NULL) return "Unknown Python Error";

    PyObject* str_excValue = PyObject_Str(value);
    const char* error_msg = PyUnicode_AsUTF8(str_excValue);

    std::string result = error_msg ? error_msg : "Error converting exception to string";

    Py_XDECREF(type);
    Py_XDECREF(value);
    Py_XDECREF(traceback);
    Py_XDECREF(str_excValue);

    return result;
}

int APIENTRY WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow) {
    std::string base_dir = GetExeDir();
    std::string tcl_env = "TCL_LIBRARY=" + base_dir + "\\DLLs\\tcl8.6";
    std::string tk_env = "TK_LIBRARY=" + base_dir + "\\DLLs\\tk8.6";
    _putenv(tcl_env.c_str());
    _putenv(tk_env.c_str());

    std::string dll_path = base_dir + "\\bin";
	SetDllDirectoryA(dll_path.c_str());

    Py_Initialize();

    const char* script = "import importlib.util; "
        "import sys; "
        "spec = importlib.util.spec_from_file_location('__main__', 'main.pyc'); "
        "module = importlib.util.module_from_spec(spec); "
        "spec.loader.exec_module(module);";

    int result = PyRun_SimpleString(script);

    if (result == -1 || result == NULL) {
        if (PyErr_Occurred()) {
            std::string err = GetPythonError();
            MessageBoxA(NULL, err.c_str(), "Python Exception", MB_ICONERROR);
        }
    }
    
    PyObject* pModule = PyImport_ImportModule("main");
    if (pModule != NULL) {
        PyObject* pFunc = PyObject_GetAttrString(pModule, "main");

        if (pFunc && PyCallable_Check(pFunc)) {
            PyObject* pArgs = PyTuple_New(0); 
            
            PyObject* pValue = PyObject_CallObject(pFunc, pArgs);
            
            if (pValue != NULL) {
                printf("Result of call: %ld\n", PyLong_AsLong(pValue));
                Py_DECREF(pValue);
            }
            Py_DECREF(pArgs);
        }
        Py_XDECREF(pFunc);
        Py_DECREF(pModule);
    }
    Py_FinalizeEx();

    return result;
}