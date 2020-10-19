# windows-api

Parses windows C/C++ headers to generate a JSON representation of the API.

# Dependencies

* ctypesgen: https://github.com/davidjamesca/ctypesgen

```
cd deps
git clone https://github.com/davidjamesca/ctypesgen
cd ctypesgen
git checkout b7ccd0764ef7d74e9ad5816924950d05b47ecc8c -b ctypesgen-1.0.2
```

### Attempt 2

Next attempt was to try pycparser.  The problem with this project is that it doesn't support parsing and representing the preprocessor data, which is required to scrape all the relevant data from the windows headerss.

* pcpp: https://pypi.org/project/pcpp/
* pycparser: https://pypi.org/project/pycparser

### Attempt 1 (Remove later)

I tried to use CppHeaderParser at first for this, but it wasn't able to parse the Windows headers, not sure why but I decided to try other projects instead.

* ply: https://pypi.org/project/ply/
* CppHeaderParser: https://pypi.org/project/CppHeaderParser/
