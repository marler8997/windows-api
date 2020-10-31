# Windows API

The Windows API in a parseable format.

This data should contain enough information to create bindings to the Windows API, including a "functional recreation" (not verbatim) of the C/C++ header files included in the Microsoft SDK.

# The "C-ish" format

The API will be maintained in a format that closely resembles C/C++ (aka "C-ish").  A tool will parse this custom format and convert it to JSON so it can easily be consumed by other tools.  This reason for making the custom format similar to `C/C++` is to make it easy to copy/paste definitions from the Microsoft SDK documentation and header files.

```c
// constant:
//     TYPE NAME = VALUE;
DWORD INVALID_HANDLE_VALUE = -1;

// typedef:
//     typedef TYPE NAME;
typedef CHAR* PCHAR;

// function:
//    TYPE NAME ( TYPE NAME, TYPE NAME, ... );
HANDLE GetStdHandle(DWORD nStdHandle);

// struct:
//    struct NAME { TYPE NAME; TYPE NAME; ... }
struct POINT { UINT x; UINT y; }
```

# Native Types

The following native types are supported and will appear the same way in the resulting json output.

* `void`
* `int`/`unsigned`: the Microsoft C `int` and `unsigned int` type, which depend on the platform.  So far, could be `16` or `32` bits.
* `uint8_t`, `uint16_t`, `uint32_t`, `uint64_t`, `size_t`: unsigned integer types
* `int8_t`, `int16_t`, `int32_t`, `int64_t`, `ssize_t`: signed integer types
* `char`: 8-bit windows ANSI character
* `wchar_t`: 16-bit unicode character
