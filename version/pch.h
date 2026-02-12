// pch.h: 这是预编译标头文件。
// 下方列出的文件仅编译一次，提高了将来生成的生成性能。
// 这还将影响 IntelliSense 性能，包括代码完成和许多代码浏览功能。
// 但是，如果此处列出的文件中的任何一个在生成之间有更新，它们全部都将被重新编译。
// 请勿在此处添加要频繁更新的文件，这将使得性能优势无效。

#ifndef PCH_H
#define PCH_H

// 添加要在此处预编译的标头
#include "framework.h"

#pragma comment(linker, "/export:GetFileVersionInfoA=c:\\windows\\system32\\version.GetFileVersionInfoA")
#pragma comment(linker, "/export:GetFileVersionInfoByHandle=c:\\windows\\system32\\version.GetFileVersionInfoByHandle")
#pragma comment(linker, "/export:GetFileVersionInfoExA=c:\\windows\\system32\\version.GetFileVersionInfoExA")
#pragma comment(linker, "/export:GetFileVersionInfoExW=c:\\windows\\system32\\version.GetFileVersionInfoExW")
#pragma comment(linker, "/export:GetFileVersionInfoSizeA=c:\\windows\\system32\\version.GetFileVersionInfoSizeA")
#pragma comment(linker, "/export:GetFileVersionInfoSizeExA=c:\\windows\\system32\\version.GetFileVersionInfoSizeExA")
#pragma comment(linker, "/export:GetFileVersionInfoSizeExW=c:\\windows\\system32\\version.GetFileVersionInfoSizeExW")
#pragma comment(linker, "/export:GetFileVersionInfoSizeW=c:\\windows\\system32\\version.GetFileVersionInfoSizeW")
#pragma comment(linker, "/export:GetFileVersionInfoW=c:\\windows\\system32\\version.GetFileVersionInfoW")
#pragma comment(linker, "/export:VerFindFileA=c:\\windows\\system32\\version.VerFindFileA")
#pragma comment(linker, "/export:VerFindFileW=c:\\windows\\system32\\version.VerFindFileW")
#pragma comment(linker, "/export:VerInstallFileA=c:\\windows\\system32\\version.VerInstallFileA")
#pragma comment(linker, "/export:VerInstallFileW=c:\\windows\\system32\\version.VerInstallFileW")
#pragma comment(linker, "/export:VerLanguageNameA=c:\\windows\\system32\\version.VerLanguageNameA")
#pragma comment(linker, "/export:VerLanguageNameW=c:\\windows\\system32\\version.VerLanguageNameW")
#pragma comment(linker, "/export:VerQueryValueA=c:\\windows\\system32\\version.VerQueryValueA")
#pragma comment(linker, "/export:VerQueryValueW=c:\\windows\\system32\\version.VerQueryValueW")

#endif //PCH_H
