#
# https://docs.microsoft.com/en-us/cpp/cpp/lexical-conventions?view=vs-2019
#

ID           = 0
DOT          = 1
EQUAL        = 2
COMMA        = 3
LEFT_PAREN   = 4
RIGHT_PAREN  = 5
NUMBER       = 6
NEWLINE_OR_COMMENT = 7
STRING       = 8
SEMICOLON    = 9
STAR         = 10
PTR_FIELD    = 11
DOUBLE_EQUAL = 12
NOT_EQUAL    = 13
BANG         = 14
INCREMENT    = 15
DECREMENT    = 16
PLUS         = 17
MINUS        = 18
SLASH        = 19
LOGICAL_OR   = 20
LOGICAL_AND  = 21
PERCENT      = 22
LEFT_CURLY   = 23
RIGHT_CURLY  = 24
LEFT_SQ_BRACKET  = 25
RIGHT_SQ_BRACKET = 26
LESS_THAN        = 27
GREATER_THAN     = 28
LESS_THAN_EQ     = 29
GREATER_THAN_EQ  = 30
HASH         = 31
TRIPLE_DOT   = 32
COLON        = 33
QUESTION     = 34
BITWISE_OR   = 35
BITWISE_AND  = 36
SINGLE_QUOTE = 37
EOF          = 38
TILDA        = 39
EXCLUSIVE_OR = 40
BACKSLASH    = 41
AT           = 42
DOLLAR       = 43

class Token:
    def __init__(self, kind, start, end):
        self.kind = kind
        self.start = start
        self.end = end
    def desc(self, str):
        return "Token {} '{}'".format(self.kind, str[self.start:self.end])
    def __repr__(self):
        return "Token {}".format(self.kind)

class StringToken(Token):
    def __init__(self, start, end, value):
        Token.__init__(self, STRING, start, end)
        self.value = value
    def desc(self, str):
        return "STRING {}".format(str[self.start:self.end])

#class NumberToken(Token):
#    def __init__(self, start, end, value):
#        Token.__init__(self, NUMBER, start, end)
#        self.value = value
#    def desc(self, str):
#        return "NUMBER {}".format(str[self.start:self.end])

def popSingleCharToken(reader, kind):
    start = reader.getPosition()
    reader.pop()
    return Token(kind, start, reader.getPosition())

def popSingleOrDoubleCharToken(reader, single_kind, second_char, double_kind):
    start = reader.getPosition()
    reader.pop()
    c = reader.peek()
    if c == second_char:
        reader.pop()
        return Token(double_kind, start, reader.getPosition())
    return Token(single_kind, start, reader.getPosition())

def popSingleOrDoubleCharToken(reader, single_kind, *args):
    start = reader.getPosition()
    reader.pop()
    c = reader.peek()
    for i in range(0, len(args), 2):
        if c == args[i]:
            reader.pop()
            return Token(args[i+1], start, reader.getPosition())
    return Token(single_kind, start, reader.getPosition())

class SyntaxError(Exception):
    pass

class Lexer:
    def __init__(self, reader):
        self.reader = reader

    def errAt(self, pos, msg):
        raise SyntaxError(self.reader.errorMessagePrefix(pos) + msg)
    def warnAt(self, pos, msg):
        print("WARNING: {}".format(self.reader.errorMessagePrefix(pos) + msg))

    def lexToken(self):
        while True:
            gotChar, c = self.skipNonBreakingSpace()
            if not gotChar:
                return Token(EOF, self.reader.getPosition(), self.reader.getPosition())

            if c >= ord('a'):
                if c <= ord('z'):
                    return lexId(self.reader)
                if c == ord('{'):
                    return popSingleCharToken(self.reader, LEFT_CURLY)
                if c == ord('}'):
                    return popSingleCharToken(self.reader, RIGHT_CURLY)
                if c == ord('|'):
                    return popSingleOrDoubleCharToken(self.reader, BITWISE_OR, ord('|'), LOGICAL_OR)
                if c == ord('~'):
                    return popSingleCharToken(self.reader, TILDA)
                raise Exception("not impl '{}'".format(chr(c)))

            if c > ord('Z'):
                if c == ord('['):
                    return popSingleCharToken(self.reader, LEFT_SQ_BRACKET)
                if c == ord(']'):
                    return popSingleCharToken(self.reader, RIGHT_SQ_BRACKET)
                if c == ord('_'):
                    return lexId(self.reader)
                if c == ord('^'):
                    return popSingleCharToken(self.reader, EXCLUSIVE_OR)
                if c == ord('\\'):
                    start = self.reader.getPosition()
                    self.reader.pop()
                    c = self.reader.peek()
                    if c == ord('\r'):
                        raise Exception("not impl, carriage return")
                    elif c == ord('\n'):
                        self.reader.pop()
                        continue
                    return Token(BACKSLASH, start, self.reader.getPosition())
                raise Exception("not impl '{}'".format(chr(c)))

            if c >= ord('A'):
                return lexId(self.reader)

            if c > ord('9'):
                if c == ord(";"):
                    return popSingleCharToken(self.reader, SEMICOLON)
                if c == ord('='):
                    return popSingleOrDoubleCharToken(self.reader, EQUAL, '=', DOUBLE_EQUAL)
                if c == ord('<'):
                    return popSingleOrDoubleCharToken(self.reader, LESS_THAN, ord('='), LESS_THAN_EQ)
                if c == ord('>'):
                    return popSingleOrDoubleCharToken(self.reader, GREATER_THAN, ord('='), GREATER_THAN_EQ)
                if c == ord(':'):
                    return popSingleCharToken(self.reader, COLON)
                if c == ord('?'):
                    return popSingleCharToken(self.reader, QUESTION)
                if c == ord('@'):
                    return popSingleCharToken(self.reader, AT)
                assert(False)

            if c >= ord('0'):
                return lexNumber(self.reader)

            if c == ord(','):
                return popSingleCharToken(self.reader, COMMA)
            if c == ord('('):
                return popSingleCharToken(self.reader, LEFT_PAREN)
            if c == ord(')'):
                return popSingleCharToken(self.reader, RIGHT_PAREN)
            if c == ord('.'):
                start = self.reader.getPosition()
                self.reader.pop()
                c = self.reader.peek()
                if c != ord('.'):
                    return Token(DOT, start, self.reader.getPosition())
                self.reader.pop()
                c = self.reader.peek()
                if c != ord('.'):
                    self.errAt(start, "found '..' that is not followed by another '.', got '{}'".format(chr(c)))
                self.reader.pop()
                return Token(TRIPLE_DOT, start, self.reader.getPosition())
            if c == ord('\n'):
                return popSingleCharToken(self.reader, NEWLINE_OR_COMMENT)
            if c == ord('"'):
                return self.lexString()
            if c == ord('*'):
                return popSingleCharToken(self.reader, STAR)
            if c == ord('!'):
                return popSingleOrDoubleCharToken(self.reader, BANG, ord('='), NOT_EQUAL)
            if c == ord('+'):
                return popSingleOrDoubleCharToken(self.reader, PLUS, ord('+'), INCREMENT)
            if c == ord('-'):
                return popSingleOrDoubleCharToken(self.reader, MINUS, ord('-'), DECREMENT, ord('>'), PTR_FIELD)
            if c == ord('/'):
                start = self.reader.getPosition()
                self.reader.pop()
                c = self.reader.peek()
                if c == ord('/'):
                    if not scanUntil(self.reader, isNewline):
                        return Token(EOF, self.reader.getPosition(), self.reader.getPosition())
                    assert(self.reader.peek() == ord('\n'))
                    self.reader.pop()
                    return Token(NEWLINE_OR_COMMENT, start, self.reader.getPosition())

                if c == ord('*'):
                    self.reader.pop()
                    at_eof, has_newline = scanMultilineComment(self.reader)
                    if at_eof:
                        return Token(EOF, self.reader.getPosition(), self.reader.getPosition())
                    if has_newline:
                        return Token(NEWLINE_OR_COMMENT, start, self.reader.getPosition())
                    continue

                return Token(SLASH, start, self.reader.getPosition())
            if c == ord('#'):
                return popSingleCharToken(self.reader, HASH)
            if c == ord('%'):
                return popSingleCharToken(self.reader, PERCENT)
            if c == ord('&'):
                return popSingleOrDoubleCharToken(self.reader, BITWISE_AND, ord('&'), LOGICAL_AND)
            if c == ord("'"):
                return popSingleCharToken(self.reader, SINGLE_QUOTE)
            if c == ord("$"):
                return popSingleCharToken(self.reader, DOLLAR)

            raise Exception("not implemented '{}' ({})".format(chr(c), c))


    def skipNonBreakingSpace(self):
        while True:
            if self.reader.atEof():
                return False, 0 # EOF
            c = self.reader.peek()
            if not isNonBreakingSpace(c):
                return True, c
            self.reader.pop()


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
                # TODO: support \x...
                escaped = STRING_ESCAPE_TABLE.get(e)
                if escaped == None:
                    chars.append(ord('\\'))
                    chars.append(e)
                    self.warnAt(escapePos, "invalid escape sequence \"{}\"".format(self.reader.str[escapePos:self.reader.getPosition() + 1]))
                else:
                    chars.append(escaped)
            elif c == ord('"'):
                break
            else:
                chars.append(c)
        self.reader.pop()
        end = self.reader.getPosition()
        return StringToken(start, end, chars.decode('utf8'))

STRING_ESCAPE_TABLE = {
    ord('n') : ord('\n'),
    ord('\\'): ord('\\'),
    ord('0') : 0,
    ord('t'): ord('\t'),
}

# returns: at_eof, has_newline
def scanMultilineComment(reader):
    has_newline = False
    while True:
        if reader.atEof():
            return True, has_newline
        c = reader.peek()
        reader.pop()
        if c == ord('*'):
            c = reader.peek()
            if c == ord('/'):
                reader.pop()
                return False, has_newline
        elif c == ord('\n'):
            has_newline = True


def isNonBreakingSpace(c):
    return c == ord(' ') or c == ord('\t') or c == ord('\f')

def isNewline(c):
    return c == ord('\n')

# assumption: reader is not at EOF
# returns: False on EOF
def scanWhile(reader, condition):
    while True:
        reader.pop()
        if reader.atEof():
            return False
        if not condition(reader.peek()):
            return True

# assumption: reader is not at EOF
# returns: False on EOF
def scanUntil(reader, condition):
    while True:
        reader.pop()
        if reader.atEof():
            return False
        if condition(reader.peek()):
            return True

def lexId(reader):
    start = reader.getPosition()
    scanWhile(reader, isIdNonFirstChar)
    return Token(ID, start, reader.getPosition())

def lexNumber(reader):
    start = reader.getPosition()
    scanWhile(reader, isNumberChar)

    # parse number postfix
    c = reader.peek()
    if c == ord('L'):
        reader.pop()

    end = reader.getPosition()
    #return NumberToken(start, end, int(reader.str[start:end]))
    return Token(NUMBER, start, end)

def isNumberChar(c):
    return (c >= ord('0') and c <= ord('9')) or c == ord('x')

def isIdNonFirstChar(c):
    if c >= ord('a'):
        return c <= ord('z')
    if c >= ord('A'):
        return c <= ord('Z') or c == ord('_')
    if c >= ord('0'):
        return c <= ord('9')
