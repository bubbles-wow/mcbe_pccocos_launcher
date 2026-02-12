// dllmain.cpp : 定义 DLL 应用程序的入口点。
#include "pch.h"

#include "MinHook.h"

#pragma comment(lib, "minhook.x64.lib")


HANDLE g_consoleHandle = INVALID_HANDLE_VALUE;

inline void DBG_LOG(const char* fmt, ...)
{
    char buf[512];
    va_list args;
    va_start(args, fmt);
    int len = vsprintf_s(buf, fmt, args);
    va_end(args);

    if (g_consoleHandle != INVALID_HANDLE_VALUE)
    {
        DWORD written;
        WriteConsoleA(g_consoleHandle, buf, (DWORD)len, &written, NULL);
    }

    OutputDebugStringA(buf);
}

bool IsGameProcess()
{
    char szFileName[MAX_PATH];
    GetModuleFileNameA(NULL, szFileName, MAX_PATH);
    std::string path = szFileName;
    std::transform(path.begin(), path.end(), path.begin(), ::tolower);

    return path.find("minecraft.windows.exe") != std::string::npos ||
        path.find("unpack_minecraft.windows.exe") != std::string::npos;
}

DWORD GetMainThreadId()
{
    DWORD dwMainThreadID = 0;
    ULONGLONG ullMinCreateTime = MAXULONGLONG;
    HANDLE hThreadSnap = CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0);
    if (hThreadSnap != INVALID_HANDLE_VALUE) {
        THREADENTRY32 te32;
        te32.dwSize = sizeof(THREADENTRY32);
        if (Thread32First(hThreadSnap, &te32)) {
            do {
                if (te32.th32OwnerProcessID == GetCurrentProcessId() && te32.th32ThreadID != GetCurrentThreadId()) {
                    HANDLE hThread = OpenThread(THREAD_QUERY_INFORMATION, FALSE, te32.th32ThreadID);
                    if (hThread) {
                        FILETIME ftCreate, ftExit, ftKernel, ftUser;
                        if (GetThreadTimes(hThread, &ftCreate, &ftExit, &ftKernel, &ftUser)) {
                            ULONGLONG ullCreateTime = ((ULONGLONG)ftCreate.dwHighDateTime << 32) | ftCreate.dwLowDateTime;
                            if (ullCreateTime < ullMinCreateTime) {
                                ullMinCreateTime = ullCreateTime;
                                dwMainThreadID = te32.th32ThreadID;
                            }
                        }
                        CloseHandle(hThread);
                    }
                }
            } while (Thread32Next(hThreadSnap, &te32));
        }
        CloseHandle(hThreadSnap);
    }
    return dwMainThreadID;
}

void OpenConsole()
{
    AllocConsole();

    g_consoleHandle = CreateFileA("CONOUT$", GENERIC_WRITE, FILE_SHARE_WRITE, NULL, OPEN_EXISTING, 0, NULL);

    FILE* fDummy;
    freopen_s(&fDummy, "CONOUT$", "w", stdout);
    freopen_s(&fDummy, "CONOUT$", "w", stderr);
}


typedef HANDLE(__stdcall* tCreateMutexA)(LPSECURITY_ATTRIBUTES lpMutexAttributes, BOOL bInitialOwner, LPCSTR lpName);
tCreateMutexA fpCreateMutexA = nullptr;

HANDLE __stdcall Detour_CreateMutexA(LPSECURITY_ATTRIBUTES lpMutexAttributes, BOOL bInitialOwner, LPCSTR lpName)
{
    DBG_LOG("[Hook] Intercepted CreateMutexA with param: %d, %d, %s\n", lpMutexAttributes, bInitialOwner, lpName);

    if (lpName && strcmp(lpName, "3f7b9d2e-6a1c-4f85-b3e2-9c0d8f1a7e4b") == 0) {
        return fpCreateMutexA(lpMutexAttributes, bInitialOwner, NULL);
    }
    return fpCreateMutexA(lpMutexAttributes, bInitialOwner, lpName);
}

void MainThread(HMODULE hModule)
{
    if (!IsGameProcess())
        return;

    if (MH_Initialize() != MH_OK)
        return;

    bool hook_2 = false;
    bool hook_3 = false;
    while (true) {
        HMODULE hModule = GetModuleHandleA("kernel32.dll");
        if (hModule) {
            LPVOID pTarget = (LPVOID)GetProcAddress(hModule, "CreateMutexA");
            if (pTarget) {
                MH_STATUS status = MH_CreateHook(pTarget, &Detour_CreateMutexA, (LPVOID*)&fpCreateMutexA);
                if (status == MH_OK && MH_EnableHook(pTarget) == MH_OK) {
                    DBG_LOG("[Hook] Successfully hooked CreateMutexA in kernel32.dll\n");
                    hook_2 = true;
                }
            }
        }
        hModule = GetModuleHandleA("kernelbase.dll");
        if (hModule) {
            LPVOID pTarget = (LPVOID)GetProcAddress(hModule, "CreateMutexA");
            if (pTarget) {
                MH_STATUS status = MH_CreateHook(pTarget, &Detour_CreateMutexA, (LPVOID*)&fpCreateMutexA);
                if (status == MH_OK && MH_EnableHook(pTarget) == MH_OK) {
                    DBG_LOG("[Hook] Successfully hooked CreateMutexA in kernelbase.dll\n");
                    hook_3 = true;
                }
            }
        }
        if (hook_2 && hook_3) {
            break;
        }

        Sleep(100);
    }
}

unsigned __stdcall ThreadWrapper(void* pContext)
{
    OpenConsole();
    HMODULE hModule = (HMODULE)pContext;
    MainThread(hModule);

    return 0;
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved)
{
    switch (ul_reason_for_call)
    {
    case DLL_PROCESS_ATTACH:
        DisableThreadLibraryCalls(hModule);

        _beginthreadex(nullptr, 0, ThreadWrapper, hModule, 0, nullptr);
        break;

    case DLL_PROCESS_DETACH:
        MH_DisableHook(MH_ALL_HOOKS);
        MH_Uninitialize();
        break;
    }
    return TRUE;
}

