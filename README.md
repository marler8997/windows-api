# windows-api

Parses windows C/C++ headers to generate a JSON representation of the API.

# Dependencies

* https://github.com/erikrose/parsimonious

```
git clone https://github.com/erikrose/parsimonious deps/parsimonious --branch 0.8.1
```

Verify sha is `f4496cc0b6bae44c09eaaf4233e94a8d70e396a9` with:
```
git -C deps/parsimonious rev-parse HEAD
```

* https://github.com/benjaminp/six

This repository is required because it is a dependency of parsimonious.

```
git clone https://github.com/benjaminp/six deps/six --branch 1.15.0
```

Verify sha is `c0be8815d13df45b6ae471c4c436cce8c192245d` with:
```
git -C deps/six rev-parse HEAD
```
