# Windows API

The Windows API in a parseable format.

This data should contain enough information to create bindings to the Windows API, including a "functional recreation" (not verbatim) of the C/C++ header files included in the Microsoft SDK.

# The JSON format

> TODO: document JSON format when it becomes more finalized
> NOTE: I use arrays instead of objects for types/constants/functions so consumers can maintain a consistent "order"

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

The more common a syntax is, the more reason there is for "C-ish" to support the C syntax.  One example where this isn't the case is function pointers, since they are rare and use an odd syntax, C-ish uses a different syntax for them.

```
// C
TYPE (*NAME)(TYPE NAME, TYPE NAME, ...)
// C-ish
funcptr TYPE(TYPE NAME, TYPE NAME, ...)
```

C-ish maintains the property that a type can be fully parsed without knowing its surrounding context and with only 1 token lookahead.  Using `funcptr` to prefix a function pointer type allows this property to be maintained, and the modified syntax also allows function pointer types to be used like normal types, where the name of the thing being defined it outside the type (i.e. `funcptr void(...) NAME` rather than `void (*NAME)(...)`).


You can declare a constant with a `void` type like this:
```c
void FALSE = 0;
void TRUE = 1;
```
This means the constant has no "type", it's just a typeless value.

Also, intead of pointer types like `T*`, you can specify `T[]` to indicate a pointer to an array of multiple items.

# TODO:

Handle macros?  Like:
```
##define MAKEWORD(a, b)      ((WORD)(((BYTE)(((DWORD_PTR)(a)) & 0xff)) | ((WORD)((BYTE)(((DWORD_PTR)(b)) & 0xff))) << 8))
##define MAKELONG(a, b)      ((LONG)(((WORD)(((DWORD_PTR)(a)) & 0xffff)) | ((DWORD)((WORD)(((DWORD_PTR)(b)) & 0xffff))) << 16))
##define LOWORD(l)           ((WORD)(((DWORD_PTR)(l)) & 0xffff))
##define HIWORD(l)           ((WORD)((((DWORD_PTR)(l)) >> 16) & 0xffff))
##define LOBYTE(w)           ((BYTE)(((DWORD_PTR)(w)) & 0xff))
##define HIBYTE(w)           ((BYTE)((((DWORD_PTR)(w)) >> 8) & 0xff))
```

# Native Types

The following native types are supported and will appear the same way in the resulting json output.

* `void`
* `int`/`unsigned`: the Microsoft C `int` and `unsigned int` type, which depend on the platform.  So far, could be `16` or `32` bits.
* `uint8_t`, `uint16_t`, `uint32_t`, `uint64_t`, `size_t`: unsigned integer types
* `int8_t`, `int16_t`, `int32_t`, `int64_t`, `ssize_t`: signed integer types
* `char`: 8-bit windows ANSI character
* `wchar_t`: 16-bit unicode character
