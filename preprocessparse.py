import preprocesslex

EOF = 0

class Node:
    def __init__(self, token):
        self.token = token
    def desc(self, str):
        return "Node {}".format(self.token.desc(str))

# TODO: remove this class once all directives have their own class
class DirectiveNode(Node):
    def __init__(self, token, directive_tokens):
        Node.__init__(self, token)
        self.directive_tokens = directive_tokens
    def desc(self, str):
        return "#{} {}".format(str[self.token.start:self.token.end], " ".join(
            [str[t.start:t.end] for t in self.directive_tokens]
        ))

class IncludeNode(Node):
    def __init__(self, include_token, filename, is_quoted):
        Node.__init__(self, include_token)
        self.filename = filename
        self.is_quoted = is_quoted
    def desc(self, str):
        return "include: {} ({})".format(self.filename, '""' if self.is_quoted else '<>')

class IfdefNode(Node):
    def __init__(self, ifdef_token, id, is_not):
        Node.__init__(self, ifdef_token)
        self.id = id
        self.is_not = is_not
    def desc(self, str):
        return "if{}def: {}".format("n" if self.is_not else "", self.id)

class IfNode(Node):
    def __init__(self, if_token, condition_tokens, expression_node):
        Node.__init__(self, if_token)
        self.condition_tokens = condition_tokens
        self.expression_node = expression_node
    def desc(self, str):
        return "if: {}: {}".format(type(self.expression_node).__name__,
                                   " ".join([str[t.start:t.end] for t in self.condition_tokens]))

class EndifNode(Node):
    def __init__(self, token):
        Node.__init__(self, token)

class ElseNode(Node):
    def __init__(self, token):
        Node.__init__(self, token)

class DefineNode(Node):
    def __init__(self, define_token, id_token, id, the_rest):
        Node.__init__(self, define_token)
        self.id_token = id_token
        self.id = id
        self.the_rest = the_rest
    def desc(self, str):
        return "Define: {} {}".format(self.id, " ".join(
            [str[t.start:t.end] for t in self.the_rest]
        ))

class DefineFuncNode(Node):
    def __init__(self, define_token, id_token, arg_tokens, the_rest):
        Node.__init__(self, define_token)
        self.id_token = id_token
        self.arg_tokens = arg_tokens
        self.the_rest = the_rest
    def desc(self, str):
        return "DefineFunc: {} ({}) {}".format(
            str[self.id_token.start:self.id_token.end],
            " , ".join([str[t.start:t.end] for t in self.arg_tokens]),
            " ".join([str[t.start:t.end] for t in self.the_rest]
        ))

class Parser:
    _STATE_LINE_START = 0
    _STATE_NOT_LINE_START = 1

    def __init__(self, lexer):
        self.lexer = lexer
        self.lookahead = []
        self.str = lexer.reader.str
        self.state = Parser._STATE_LINE_START

    def errAt(self, token, msg):
        self.lexer.errAt(token.start, msg)

    def peekToken(self):
        if not self.lookahead:
            self.lookahead.append(self.lexer.lexToken())
        return self.lookahead[0]

    def popToken(self):
        assert(self.lookahead)
        self.lookahead.pop(0)

    def popExpectedToken(self, expected_kind):
        token = self.peekToken()
        self.popToken()
        if token.kind != expected_kind:
            raise self.errAt(token, "expected token {} but got {}: {}".format(
                expected_kind, token.kind, token.desc(self.str)))
        return token

    def parseInto(self, nodes):
        while True:
            node = self.parseNode()
            if node.token.kind == preprocesslex.EOF:
                break
            nodes.append(node)

    def parseNode(self):
        while True:
            token = self.peekToken()
            if token.kind == preprocesslex.EOF:
                return Node(token)
            self.popToken()
            if self.state == Parser._STATE_LINE_START:
                if token.kind == preprocesslex.HASH:
                    node = self.parseDirective()
                    if node:
                        return node
            if token.kind == preprocesslex.NEWLINE_OR_COMMENT:
                self.state = Parser._STATE_LINE_START
                continue
            self.state = Parser._STATE_NOT_LINE_START
            return Node(token)

    def parseDirective(self):
        id_token = self.peekToken()
        self.popToken()
        if id_token.kind != preprocesslex.ID:
            # looks like there is a case where we have an empty '#' with no directive!
            if id_token.kind == preprocesslex.NEWLINE_OR_COMMENT:
                return None
            raise self.errAt(id_token, "expected ID after '#' but got {}".format(id_token.desc(self.str)))
        id = self.str[id_token.start:id_token.end]
        if id == "include":
            return self.parseIncludeDirective(id_token)
        if id == "define":
            return self.parseDefineDirective(id_token)
        if id == "pragma":
            return self.skipDirective(id_token, True)
        if id == "ifdef":
            return self.parseIfdefDirective(id_token, False)
        if id == "ifndef":
            return self.parseIfdefDirective(id_token, True)
        if id == "if":
            return self.parseIfDirective(id_token)
        if id == "elif":
            return self.skipDirective(id_token, False)
        if id == "else":
            return self.parseElseDirective(id_token)
        if id == "endif":
            return self.parseEndifDirective(id_token)
        if id == "undef":
            return self.skipDirective(id_token, True)
        if id == "error":
            return self.skipDirective(id_token, True)

        raise self.errAt(id_token, "unknown directive '#{}'".format(id))

    # returns (at_eof, tokens)
    def scanTokensTo(self, to_kind, include_to_token):
        tokens = []
        while True:
            token = self.peekToken()
            if token.kind == preprocesslex.EOF:
                return True, tokens
            self.popToken()
            if token.kind == to_kind:
                if include_to_token:
                    tokens.append(token)
                return False, tokens
            tokens.append(token)

    def skipToNewline(self):
        while True:
            token = self.peekToken()
            if token.kind == preprocesslex.EOF:
                return token
            self.popToken()
            if  token.kind == preprocesslex.NEWLINE_OR_COMMENT:
                return token

    def skipInlineTokensTo(self, to_kind):
        while True:
            token = self.peekToken()
            if token.kind == preprocesslex.EOF:
                return token
            self.popToken()
            if  token.kind == to_kind or token.kind == preprocesslex.NEWLINE_OR_COMMENT:
                return token

    def parseIfdefDirective(self, ifdef_token, is_not):
        id_token = self.peekToken()
        if id_token.kind != preprocesslex.ID:
            raise self.errAt("expected an ID after #if[n]def but got: {}".format(id_token.desc(self.str)))
        self.popToken()
        return IfdefNode(ifdef_token, self.str[id_token.start:id_token.end], is_not)

    def parseIfDirective(self, if_token):
        at_eof, tokens = self.scanTokensTo(preprocesslex.NEWLINE_OR_COMMENT, False)
        if len(tokens) == 0:
            raise self.errAt(if_token, "#if requires an expression")
        return IfNode(if_token, tokens, self.parseCompleteExpression(tokens))

    def parseEndifDirective(self, id_token):
        # some windows #endif directives contain tokens, just going to ignore them
        _ = self.skipToNewline()
        return EndifNode(id_token)

    def parseElseDirective(self, id_token):
        # some windows #else directives contain tokens, just going to ignore them
        _ = self.skipToNewline()
        return ElseNode(id_token)

    def parseIncludeDirective(self, include_token):
        first_token = self.peekToken()
        if first_token.kind == preprocesslex.STRING:
            return IncludeNode(include_token, first_token.value, True)

        if first_token.kind != preprocesslex.LESS_THAN:
            raise self.errAt(first_token, "expected '<' or '\"' after #include but got: {}".format(first_token.desc(self.str)))
        file_start = first_token.end
        close_token = self.skipInlineTokensTo(preprocesslex.GREATER_THAN)
        if close_token.kind != preprocesslex.GREATER_THAN:
            raise self.errAt(close_token, "unclosed #include <...> directive")
        return IncludeNode(include_token, self.str[file_start:close_token.start], False)

    def parseDefineDirective(self, define_token):
        id_token = self.peekToken()
        if id_token.kind != preprocesslex.ID:
            raise self.errAt(id_token, "#define expects an ID but got: {}".format(id_token.desc(self.str)))
        self.popToken()
        after_id_token = self.peekToken()
        if after_id_token.kind == preprocesslex.LEFT_PAREN and after_id_token.start == id_token.end:
            return self.parseDefineFuncDirective(define_token, id_token)

        at_eof, tokens = self.scanTokensTo(preprocesslex.NEWLINE_OR_COMMENT, False)
        return DefineNode(define_token, id_token, self.str[id_token.start:id_token.end], tokens)

    # points to the left paren token
    def parseDefineFuncDirective(self, define_token, id_token):
        self.popToken()
        arg_tokens = []
        while True:
            next_token = self.peekToken()
            if next_token.kind == preprocesslex.EOF:
                raise self.errAt(define_token, "#define function missing closing paren")
            if next_token.kind == preprocesslex.RIGHT_PAREN:
                break
            if len(arg_tokens) > 0:
                if next_token.kind != preprocesslex.COMMA:
                    raise self.errAt(define_token, "expected ',' or ')' but got: {}".format(next_token.desc(self.str)))
                self.popToken()
                next_token = self.peekToken()
            if next_token.kind == preprocesslex.TRIPLE_DOT:
                arg_tokens.append(next_token)
                self.popToken()
                next_token = self.peekToken()
                if next_token.kind != preprocesslex.RIGHT_PAREN:
                    self.errAt(next_token, "expected ')' after '...' bug got: {}".format(next_token.desc(self.str)))
                break
            if next_token.kind != preprocesslex.ID:
                raise self.errAt(define_token, "expected ID but got: {}".format(next_token.desc(self.str)))
            arg_tokens.append(next_token)
            self.popToken()
        self.popToken()
        at_eof, tokens = self.scanTokensTo(preprocesslex.NEWLINE_OR_COMMENT, False)
        return DefineFuncNode(define_token, id_token, arg_tokens, tokens)

    def skipDirective(self, directive_token, allow_eof):
        at_eof, tokens = self.scanTokensTo(preprocesslex.NEWLINE_OR_COMMENT, False)
        if at_eof and (not allow_eof):
            raise self.errAt(directive_token, "unmatched {}".format(self.str[directive_token.start:directive_token.end]))
        return DirectiveNode(directive_token, tokens)

    def parseCompleteExpression(self, tokens):
        import parsimoniousdeps
        import parsimonious
        import cexpr
        assert(len(tokens) > 0)
        # this doesn't work becuase it bring back line continuations
        #expr_src = self.str[tokens[0].start:tokens[-1].end]
        expr_src = " ".join([self.str[t.start:t.end] for t in tokens])
        #print("tokens: {}".format(tokens))
        #print("[DEBUG] parsing '{}'".format(expr_src))
        try:
            expr_node = cexpr.GRAMMAR.parse(expr_src)
        except parsimonious.exceptions.ParseError as e:
            raise self.errAt(tokens[0], "expression parse failed: {}".format(e))
        return NotImplementedExpression()

class Expression:
    pass
class BinaryExpression(Expression):
    def __init__(self, op_token, expr1, expr2):
        self.op_token = op_token
        self.expr1 = expr1
        self.expr2 = expr2
class LogicalOrExpression(BinaryExpression):
    def __init__(self, op_token, expr1, expr2):
        BinaryExpression.__init__(self, op_token, expr1, expr2)
class LogicalAndExpression(Expression):
    def __init__(self, op_token, expr1, expr2):
        BinaryExpression.__init__(self, op_token, expr1, expr2)
class BitwiseOrExpression(Expression):
    def __init__(self, op_token, expr1, expr2):
        BinaryExpression.__init__(self, op_token, expr1, expr2)
class ExclusiveOrExpression(Expression):
    def __init__(self, op_token, expr1, expr2):
        BinaryExpression.__init__(self, op_token, expr1, expr2)
class BitwiseAndExpression(Expression):
    def __init__(self, op_token, expr1, expr2):
        BinaryExpression.__init__(self, op_token, expr1, expr2)
class EqualityExpression(Expression):
    def __init__(self, op_token, expr1, expr2):
        BinaryExpression.__init__(self, op_token, expr1, expr2)
class RelationalExpression(Expression):
    def __init__(self, op_token, expr1, expr2):
        BinaryExpression.__init__(self, op_token, expr1, expr2)
class ShiftExpression(Expression):
    def __init__(self, op_token, expr1, expr2):
        BinaryExpression.__init__(self, op_token, expr1, expr2)
class AdditiveExpression(Expression):
    def __init__(self, op_token, expr1, expr2):
        BinaryExpression.__init__(self, op_token, expr1, expr2)
class MultiplicativeExpression(Expression):
    def __init__(self, op_token, expr1, expr2):
        BinaryExpression.__init__(self, op_token, expr1, expr2)
class UnaryExpression(Expression):
    def __init__(self, op_token, expr):
        self.op_token = op_token
        self.expr = expr
class NotImplementedExpression(Expression):
    pass
class NumberExpression(Expression):
    def __init__(self, number_token):
        self.number_token = number_token
class StringExpression(Expression):
    def __init__(self, string_token):
        self.string_token = string_token
class MacroSymbolExpression(Expression):
    def __init__(self, id_token, id):
        self.id_token = id_token
        self.id = id
class DefinedExpression(Expression):
    def __init__(self, define_token, expr):
        self.define_token = define_token
        self.expr = expr
