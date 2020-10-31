import errors

class StringReader:
    def __init__(self, str, filenameForErrors):
        self.str = str
        self.index = 0
        self.filenameForErrors = filenameForErrors
    def atEof(self):
        return self.index == len(self.str)
    def getPosition(self):
        return self.index
    def peek(self):
        assert(not self.atEof())
        return ord(self.str[self.index])
    def pop(self):
        assert(not self.atEof())
        self.index += 1
    def errorMessagePrefix(self, pos):
        lineno, col = errors.getLineAndCol(self.str[:pos])
        if self.filenameForErrors:
            return "{}({}:{}) ".format(self.filenameForErrors, lineno, col)
        return "line {} col {}: ".format(lineno, col)
