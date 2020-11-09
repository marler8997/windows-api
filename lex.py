TOKEN_KINDS = (
    ("ID",None),
    ("ID_SPECIAL",None),
    ("NUMBER",None),
    ("LEFT_PAREN","("),
    ("RIGHT_PAREN",")"),
    ("SEMICOLON",";"),
    ("LEFT_CURLY","{"),
    ("RIGHT_CURLY","}"),
    ("STAR","*"),
    ("DASH","-"),
    ("LEFT_BRACKET","["),
    ("RIGHT_BRACKET","]"),
    ("EOF",None),
    ("COMMA",","),
    ("STRING",None),
    ("EQUAL","="),
    ("UNSUPPORTED",None),
)

class TokenKind:
    def __init__(self, num, name, val):
        self.num = num
        self.name = name
        self.val = val
    def __eq__(self, other):
        return self.num == other.num
    def __repr__(self):
        return self.val if self.val else self.name

def createTokenVars():
    next_num = 0
    for kind,val in TOKEN_KINDS:
        globals()[kind] = TokenKind(next_num, kind, val)
        next_num += 1
createTokenVars()

class Token:
    def __init__(self, kind, start, end):
        self.kind = kind
        self.start = start
        self.end = end
    def desc(self, str):
        if self.kind == EOF:
            return "EOF"
        assert(self.end > self.start)
        return str[self.start:self.end]
        #if self.kind == ID:
        #    return "ID({})".format(str[self.start:self.end])
        #if self.kind == UNSUPPORTED:
        #    return "UNSUPPORTED({})".format(str[self.start:self.end])
        #return self.kind.name

class StringToken(Token):
    def __init__(self, start, end, value):
        Token.__init__(self, STRING, start, end)
        self.value = value
    def desc(self, str):
        return "STRING {}".format(str[self.start:self.end])

class NumberToken(Token):
    def __init__(self, start, end, value):
        Token.__init__(self, NUMBER, start, end)
        self.value = value
    def desc(self, str):
        return "NUMBER {}".format(str[self.start:self.end])

def popSingleCharToken(reader, kind):
    start = reader.getPosition()
    reader.pop()
    return Token(kind, start, reader.getPosition())

class SyntaxError(Exception):
    pass

class Lexer:
    def __init__(self, reader):
        self.reader = reader

    def errAt(self, pos, msg):
        raise SyntaxError(self.reader.errorMessagePrefix(pos) + msg)

    def lexToken(self):
        gotCharFromSkipTrivial, c = self.skipTrivial()
        if not gotCharFromSkipTrivial:
            return Token(EOF, self.reader.getPosition(), self.reader.getPosition())

        if c >= ord('a'):
            if c <= ord('z'):
                return self.lexId(False)
            if c == ord('{'):
                return popSingleCharToken(self.reader, LEFT_CURLY)
            if c == ord('}'):
                return popSingleCharToken(self.reader, RIGHT_CURLY)
            if c == ord('|'):
                return popSingleCharToken(self.reader, PIPE)
            if c == ord('~'):
                return popSingleCharToken(self.reader, TILDA)
            return popSingleCharToken(self.reader, CHAR_OUT_OF_RANGE)

        if c > ord('Z'):
            if c == ord('['):
                return popSingleCharToken(self.reader, LEFT_BRACKET)
            elif c == ord(']'):
                return popSingleCharToken(self.reader, RIGHT_BRACKET)
            return popSingleCharToken(self.reader, UNSUPPORTED)
        if c >= ord('A'):
            return self.lexId(False)
        if c > ord('9'):
            if c == ord(';'):
               return popSingleCharToken(self.reader, SEMICOLON)
            elif c == ord('='):
                return popSingleCharToken(self.reader, EQUAL)
            elif c == ord('@'):
                return self.lexId(True)
            else:
                return popSingleCharToken(self.reader, UNSUPPORTED)
        if c >= ord('0'):
            return lexNumber(self.reader)
        if c == ord('.'):
            return popSingleCharToken(self.reader, DOT)
        if c == ord('('):
            return popSingleCharToken(self.reader, LEFT_PAREN)
        if c == ord(')'):
            return popSingleCharToken(self.reader, RIGHT_PAREN)
        if c == ord(','):
            return popSingleCharToken(self.reader, COMMA)
        if c == ord('*'):
            return popSingleCharToken(self.reader, STAR)
        if c == ord('-'):
            return popSingleCharToken(self.reader, DASH)
        if c == ord('"'):
            return self.lexString()

        return popSingleCharToken(self.reader, UNSUPPORTED)

    # returns: 0 on EOF, otherwise, the next char
    def skipTrivial(self):
        while True:
            if self.reader.atEof():
                return False, 0 # EOF
            c = self.reader.peek()
            if c == ord(' ') or c == ord('\n'):
                self.reader.pop()
                continue
            if c == ord('#'):
                while True:
                    self.reader.pop()
                    if self.reader.atEof():
                        return False, 0 # EOF
                    c = self.reader.peek()
                    if c == ord('\n'):
                        break
                continue
            return True, c

    # reader points to open quote
    def lexString(self):
        start = self.reader.getPosition()
        chars = bytearray()
        while True:
            self.reader.pop()
            if self.reader.atEof():
                self.errAt(start, "quoted-string is missing close quote")
            c = self.reader.peek()
            if c == ord('\\'):
                escapePos = self.reader.getPosition()
                self.reader.pop()
                if self.reader.atEof():
                    self.errAt(escapePos, "unfinished escape sequence")
                e = self.reader.peek()
                if e == ord('n'):
                    chars.append(ord('\n'))
                else:
                    self.reader.pop()
                    self.errAt(escapePos, "invalid escape sequence \"{}\"".format(self.reader.str[escapePos:self.reader.getPosition()]))
            elif c == ord('"'):
                break
            else:
                chars.append(c)
        self.reader.pop()
        end = self.reader.getPosition()
        return StringToken(start, end, chars.decode('utf8'))

    def lexId(self, is_special):
        start = self.reader.getPosition()
        if is_special:
            self.reader.pop()
            c = self.reader.peek()
            if not isIdChar(c):
                self.errAt(self.reader.getPosition(), "expected an ID char after '@' but got '{}' (ascii code {})".format(chr(c), c))
        scanWhile(self.reader, isIdChar)
        return Token(ID_SPECIAL if is_special else ID, start, self.reader.getPosition())

# assumption: reader is not at EOF
# returns: False on EOF
def scanWhile(reader, condition):
    while True:
        reader.pop()
        if reader.atEof():
            return False
        if not condition(reader.peek()):
            return True

def isOctalChar(c):
    return c >= ord('0') and c <= ord('7')
def isDecimalChar(c):
    return c >= ord('0') and c <= ord('9')
def isHexChar(c):
    if c <= ord('9'):
        return c >= ord('0')
    if c >= ord('a'):
        return c <= ord('f')
    return c <= ord('F') and c >= ord('A')

def lexNumber(reader):
    start = reader.getPosition()
    c = reader.peek()
    if c != ord('0'):
        scanWhile(reader, isDecimalChar)
    else:
        reader.pop()
        if not reader.atEof():
            c = reader.peek()
            if c == ord("x") or c == ord("X"):
                scanWhile(reader, isHexChar)
            elif isOctalChar(c):
                scanWhile(reader, isOctalChar)

    end = reader.getPosition()
    return NumberToken(start, end, reader.str[start:end])

def isNonQuoteChar(c):
    return c != ord('"')

def isNumberChar(c):
    return (c >= ord('0')) and (c <= ord('9'))

def isIdChar(c):
    if c >= ord('a'):
        return c <= ord('z')
    if c >= ord('A'):
        return c <= ord('Z') or c == ord('_')
    if c >= ord('0'):
        return c <= ord('9')
