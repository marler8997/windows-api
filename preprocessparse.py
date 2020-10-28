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

    # https://gcc.gnu.org/onlinedocs/cpp/If.html
    # Condition can contain
    #   - integer constants
    #   - character constants
    #   - Arithmetic operators for addition, subtraction, multiplication, division, bitwise operations, shifts, comparisons, and logical operations (&& and ||). The latter two obey the usual short-circuiting rules of standard C.
    #   - macros
    #   - the 'defined' operator
    #   - Identifiers that are not macros, which are all considered to be the number zero. This allows you to write #if MACRO instead of #ifdef MACRO, if you know that MACRO, when defined, will always have a nonzero value. Function-like macros used without their function call parentheses are also treated as zero.
    def parseCompleteExpression(self, tokens):
        # TODO: try to parse using peg
        #self.parseCompleteExpressionCustom(tokens)
        self.parseCompleteExpressionPeg(tokens)
    def parseCompleteExpressionPeg(self, tokens):
        import parsimoniousdeps
        import parsimonious
        import cexpr
        assert(len(tokens) > 0)
        #expr_src = self.str[tokens[0].start:tokens[-1].end]
        expr_src = " ".join([self.str[t.start:t.end] for t in tokens])
        #print("tokens: {}".format(tokens))
        print("[DEBUG] parsing '{}'".format(expr_src))
        try:
            expr_node = cexpr.GRAMMAR.parse(expr_src)
        except parsimonious.exceptions.ParseError as e:
            raise self.errAt(tokens[0], "expression parse failed: {}".format(e))
        return NotImplementedExpression()
    def parseCompleteExpressionCustom(self, tokens):
        assert(len(tokens) > 0)
        # TODO: support parseConditionalExpression?
        expr, tokens = self.parseExpression(tokens)
        if tokens:
            raise self.errAt(tokens[0], "extra tokens after full expression was parsed")
        return expr
    def parseBinaryOp(self, tokens, token_kinds, ExprClass, next_func):
        expr, tokens = next_func(tokens)
        if (not tokens) or  (not (tokens[0].kind in token_kinds)):
            return expr, tokens
        op_token = tokens[0]
        tokens = tokens[1:]
        if len(tokens) == 0:
            raise self.errAt(op_token, "missing expression after '{}'".format(self.str[op_token.start:op_token.end]))
        return ExprClass(op_token, expr, self.parseCompleteExpression(tokens)), None
    def parseExpression(self, tokens):
        return self.parseLogicalOrExpression(tokens)
    # TODO: turn these binary op functions into a single function with a loop?
    def parseLogicalOrExpression(self, tokens):
        return self.parseBinaryOp(tokens, [preprocesslex.LOGICAL_OR], LogicalOrExpression, self.parseLogicalAndExpression)
    def parseLogicalAndExpression(self, tokens):
        return self.parseBinaryOp(tokens, [preprocesslex.LOGICAL_AND], LogicalAndExpression, self.parseBitwiseOrExpression)
    def parseBitwiseOrExpression(self, tokens):
        return self.parseBinaryOp(tokens, [preprocesslex.BITWISE_OR], BitwiseOrExpression, self.parseExclusiveOrExpression)
    def parseExclusiveOrExpression(self, tokens):
        return self.parseBinaryOp(tokens, [preprocesslex.EXCLUSIVE_OR], ExclusiveOrExpression, self.parseBitwiseAndExpression)
    def parseBitwiseAndExpression(self, tokens):
        return self.parseBinaryOp(tokens, [preprocesslex.BITWISE_AND], BitwiseAndExpression, self.parseEqualityExpression)
    def parseEqualityExpression(self, tokens):
        return self.parseBinaryOp(tokens, [preprocesslex.DOUBLE_EQUAL, preprocesslex.NOT_EQUAL], EqualityExpression, self.parseRelationalExpression)
    def parseRelationalExpression(self, tokens):
        return self.parseBinaryOp(tokens, [
            preprocesslex.LESS_THAN,
            preprocesslex.GREATER_THAN,
            preprocesslex.LESS_THAN_EQ,
            preprocesslex.GREATER_THAN_EQ,
        ], RelationalExpression, self.parseAdditiveExpression)
    # TODO: support shift expression << and >>?
    #def parseShiftExpression(self, tokens):
    def parseAdditiveExpression(self, tokens):
        return self.parseBinaryOp(tokens, [preprocesslex.PLUS, preprocesslex.MINUS], AdditiveExpression, self.parseMultiplicativeExpression)
    def parseMultiplicativeExpression(self, tokens):
        return self.parseBinaryOp(tokens, [preprocesslex.STAR, preprocesslex.SLASH, preprocesslex.PERCENT], MultiplicativeExpression, self.parseUnaryExpression)

    def parseCastExpression(self, tokens):
        '''
        cast_expression
            ::= unary_expression
            | '(' type_name ')' cast_expression
        '''
        # TODO: do I need to support cast expression?
        # for now, just don't support them
        return self.parseUnaryExpression(tokens)

    def parseUnaryExpression(self, tokens):
        '''
        unary_expression
            ::= postfix_expression
            | INC_OP unary_expression
            | DEC_OP unary_expression
            | unary_operator cast_expression
            | SIZEOF unary_expression
            | SIZEOF '(' type_name ')'
        '''
        next_token = tokens[0]
        next_token_str = self.str[next_token.start:next_token.end]

        if next_token.kind in [preprocesslex.INCREMENT, preprocesslex.DECREMENT]:
            op_token = next_token
            tokens = tokens[1:]
            if len(tokens) == 0:
                raise self.errAt(op_token, "expected an expression after '{}'".format(self.str[op_token.start:op_token.end]))
            expr, tokens = self.parseUnaryExpression(tokens)
            return UnaryExpression(op_token, expr), tokens
        if next_token.kind in [
                preprocesslex.BITWISE_AND,
                preprocesslex.STAR,
                preprocesslex.PLUS,
                preprocesslex.MINUS,
                preprocesslex.TILDA,
                preprocesslex.BANG,
        ]:
            op_token = next_token
            tokens = tokens[1:]
            if len(tokens) == 0:
                raise self.errAt(op_token, "expected an expression after '{}'".format(self.str[op_token.start:op_token.end]))
            expr, tokens = self.parseCastExpression(tokens)
            return UnaryExpression(op_token, expr), tokens

        if next_token.kind == preprocesslex.ID and next_token_str == "sizeof":
            raise self.errAt(next_token, "sizeof not implemented")

        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # TODO: I think this is where I would check for 'defined'
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        return self.parsePostfixExpression(tokens)

    def parsePostfixExpression(self, tokens):
        '''
        postfix_expression
            ::= primary_expression
            | postfix_expression '[' expression ']'
            | postfix_expression '(' ')'
            | postfix_expression '(' argument_expression_list ')'
            | postfix_expression '.' IDENTIFIER
            | postfix_expression PTR_OP IDENTIFIER
            | postfix_expression INC_OP
            | postfix_expression DEC_OP
        '''
        expr, tokens = self.parsePrimaryExpression(tokens)
        if tokens:
            next_token = tokens[0]
            if next_token.kind == preprocesslex.LEFT_SQ_BRACKET:
                return NotImplementedExpression(), None
            if next_token.kind == preprocesslex.LEFT_PAREN:
                return NotImplementedExpression(), None
            if next_token.kind == preprocesslex.DOT:
                # TODO: verify/ensure next token is an identifier
                return NotImplementedExpression(), None
            if next_token.kind == preprocesslex.PTR_FIELD:
                return NotImplementedExpression(), None
            if next_token.kind == preprocesslex.INCREMENT:
                return NotImplementedExpression(), None
            if next_token.kind == preprocesslex.DECREMENT:
                return NotImplementedExpression(), None

        return expr, tokens

    def parsePrimaryExpression(self, tokens):
        '''
        primary_expression
            ::= IDENTIFIER
            | CONSTANT
            | STRING_LITERAL
            | '(' expression ')'

        Note that I'm also handing the 'defined' operator here:
            | 'defined' ['('] ID [')']
        '''
        next_token = tokens[0]
        if next_token.kind == preprocesslex.NUMBER:
            return NumberExpression(next_token), tokens[1:]
        if next_token.kind == preprocesslex.STRING:
            return StringExpression(next_token), tokens[1:]
        if next_token.kind == preprocesslex.ID:
            next_token_str = self.str[next_token.start:next_token.end]
            if next_token_str == "defined":
                return self.parseDefinedOp(next_token, tokens[1:])

            # TODO: remove these next 2 lines once I fix bugs
            if len(tokens) != 1:
                return NotImplementedExpression(), None
            return MacroSymbolExpression(next_token, next_token_str), tokens[1:]

        if next_token.kind == preprocesslex.LEFT_PAREN:
            # TODO: remove this next line once bugs are fixed
            return NotImplementedExpression(), None

            tokens = tokens[1:]
            if len(tokens) == 0:
                raise self.errAt(next_token, "expected expressiona after '('")
            expr, tokens = self.parseExpression(tokens)
            if not tokens:
                raise self.errAt(next_token, "missing closing paren ')'")
            if tokens[0].kind != preprocesslex.RIGHT_PAREN:
                raise self.errAt(tokens[0], "expected ')' but got '{}'".format(self.str[tokens[0].start:tokens[0].end]))
            return expr, tokens[1:]

        raise self.errAt(next_token, "unexpected token in primary expression: {}".format(next_token.desc(self.str)))

    def parseDefinedOp(self, defined_token, tokens):
        if len(tokens) == 0:
            raise self.errAt(next_token, "the 'defined' operator requires an ID")
        next_token = tokens[0]
        if next_token.kind == preprocesslex.LEFT_PAREN:
            using_parens = True
            if len(tokens) <= 1:
                raise self.errAt(next_token, "missing ID and ')' after 'defined'")
            tokens = tokens[1:]
            next_token = tokens[0]
        else:
            using_parens = False

        if next_token.kind != preprocesslex.ID:
            raise self.errAt(next_token, "defined operator requires an ID but got: {}".format(next_token.desc(self.str)))
        id_token = next_token
        tokens = tokens[1:]
        id = self.str[id_token.start:id_token.end]

        if using_parens:
            if len(tokens) == 0:
                raise self.errAt(next_token, "missing ')' after 'defined(ID'")
            if tokens[0].kind != preprocesslex.RIGHT_PAREN:
                raise self.errAt(next_token, "expected ')' after 'defined(ID' but got: {}".format(tokens[0].desc(self.str)))
            tokens = tokens[1:]

        return DefinedExpression(id_token, id), tokens

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

'''
constant_expression
	::= conditional_expression

conditional_expression
	::= logical_or_expression
	| logical_or_expression '?' expression ':' conditional_expression

logical_or_expression
	::= logical_and_expression
	| logical_or_expression OR_OP logical_and_expression

logical_and_expression
	::= bitwise_or_expression
	| logical_and_expression AND_OP bitwise_or_expression

bitwise_or_expression
	::= exclusive_or_expression
	| bitwise_or_expression '|' exclusive_or_expression

exclusive_or_expression
	::= and_expression
	| exclusive_or_expression '^' and_expression

and_expression
	::= equality_expression
	| and_expression '&' equality_expression

equality_expression
	::= relational_expression
	| equality_expression EQ_OP relational_expression
	| equality_expression NE_OP relational_expression

relational_expression
	::= shift_expression
	| relational_expression '<' shift_expression
	| relational_expression '>' shift_expression
	| relational_expression LE_OP shift_expression
	| relational_expression GE_OP shift_expression

shift_expression
	::= additive_expression
	| shift_expression LEFT_OP additive_expression
	| shift_expression RIGHT_OP additive_expression

additive_expression
	::= multiplicative_expression
	| additive_expression '+' multiplicative_expression
	| additive_expression '-' multiplicative_expression

multiplicative_expression
	::= cast_expression
	| multiplicative_expression '*' cast_expression
	| multiplicative_expression '/' cast_expression
	| multiplicative_expression '%' cast_expression

cast_expression
	::= unary_expression
	| '(' type_name ')' cast_expression

unary_operator
	::= '&'
	| '*'
	| '+'
	| '-'
	| '~'
	| '!'

unary_expression
	::= postfix_expression
	| INC_OP unary_expression
	| DEC_OP unary_expression
	| unary_operator cast_expression
	| SIZEOF unary_expression
	| SIZEOF '(' type_name ')'

argument_expression_list
	::= assignment_expression
	| argument_expression_list ',' assignment_expression

postfix_expression
	::= primary_expression
	| postfix_expression '[' expression ']'
	| postfix_expression '(' ')'
	| postfix_expression '(' argument_expression_list ')'
	| postfix_expression '.' IDENTIFIER
	| postfix_expression PTR_OP IDENTIFIER
	| postfix_expression INC_OP
	| postfix_expression DEC_OP

primary_expression
	::= IDENTIFIER
	| CONSTANT
	| STRING_LITERAL
	| '(' expression ')'
'''
