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
        visitor = ToExpressionVisitor()
        visitor.visit(expr_node)
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

def isEmpty(node):
    return node.start == node.end
def verifyChildren(node, *names):
    assert(len(node.children) == len(names))
    for i in range(0, len(names)):
        if names[i]:
            assert(node.children[i].expr_name == names[i])
class ToExpressionVisitor:
    def visit(self, node):
        if not node.expr_name:
            raise Exception("visit method without an expression name: {}".format(node.expr.as_rule()))
        method_name = 'visit' + node.expr_name
        method = getattr(self, method_name)
        if not method:
            sys.exit("Error: '{}' is not defined".format(method_name))
        return method(node)

    def visitExpression(self, node):
        verifyChildren(node, "AssignmentExpression", None)
        self.visit(node.children[0])
        if not isEmpty(node.children[1]):
            sys.exit("not impl")
    def visitAssignmentExpression(self, node):
        if node.children[0].expr_name == "ConditionalExpression":
            verifyChildren(node, "ConditionalExpression")
            self.visit(node.children[0])
        else:
            sys.exit("not impl assign expr")
    def visitConditionalExpression(self, node):
        verifyChildren(node, "LogicalORExpression", None)
        self.visit(node.children[0])
        if not isEmpty(node.children[1]):
            sys.exit("not impl conditional expr")

    def visitBinaryExpression(self, node, op_expr_names, next_expr_name):
        # SomeBinaryExpression = NextBinaryExpression (OP NextBinaryExpression)*
        verifyChildren(node, next_expr_name, None)
        self.visit(node.children[0])
        node = node.children[1]
        for node in node.children:
            verify_op_name = None if (len(op_expr_names) != 1) else op_expr_names[0]
            verifyChildren(node, verify_op_name, next_expr_name)
            if not verify_op_name:
                verifyChildren(node.children[0], None)
                assert(node.children[0].children[0].expr_name in op_expr_names)
            self.visit(node.children[1])
    def visitLogicalORExpression(self, node):
        self.visitBinaryExpression(node, ("OROR",), "LogicalANDExpression")
    def visitLogicalANDExpression(self, node):
        self.visitBinaryExpression(node, ("ANDAND",), "InclusiveORExpression")
    def visitInclusiveORExpression(self, node):
        self.visitBinaryExpression(node, ("OR",), "ExclusiveORExpression")
    def visitExclusiveORExpression(self, node):
        self.visitBinaryExpression(node, ("HAT",), "ANDExpression")
    def visitANDExpression(self, node):
        self.visitBinaryExpression(node, ("AND",), "EqualityExpression")
    def visitEqualityExpression(self, node):
        self.visitBinaryExpression(node, ("EQUEQU","BANGEQU"), "RelationalExpression")
    def visitRelationalExpression(self, node):
        self.visitBinaryExpression(node, ("LE", "GE", "LT", "GT"), "ShiftExpression")
    def visitShiftExpression(self, node):
        self.visitBinaryExpression(node, ("LEFT", "RIGHT"), "AdditiveExpression")
    def visitAdditiveExpression(self, node):
        self.visitBinaryExpression(node, ("PLUS", "MINUS"), "MultiplicativeExpression")
    def visitMultiplicativeExpression(self, node):
        self.visitBinaryExpression(node, ("STAR", "DIV", "MOD"), "CastExpression")

    def visitUnaryExpression(self, node):
        # TODO: support sizeof?
        # UnaryExpression = PostfixExpression / (INC UnaryExpression) / (DEC UnaryExpression) / (UnaryOperator CastExpression)
        verifyChildren(node, None)
        node = node.children[0]
        if node.expr_name == "PostfixExpression":
            self.visit(node)
        else:
            assert(not node.expr_name)
            first = node.children[0]
            if first.expr_name == "INC":
                verifyChildren(node, "INC", "UnaryExpression")
                print("INC")
                self.visit(node.children[1])
            elif first.expr_name == "DEC":
                verifyChildren(node, "DEC", "UnaryExpression")
                print("DEC")
                self.visit(node.children[1])
            elif first.expr_name == "UnaryOperator":
                verifyChildren(node, "UnaryOperator", "CastExpression")
                print("Unary({})".format(node.children[0].text))
                self.visit(node.children[1])

    def visitCastExpression(self, node):
        verifyChildren(node, "UnaryExpression")
        self.visit(node.children[0])

    def visitPostfixExpression(self, node):
        '''
        PostfixExpression = PrimaryExpression (
            (LBRK Expression RBRK)
          / (LPAR ArgumentExpressionList? RPAR)
          / (DOT Identifier)
          / (PTR Identifier)
          / INC
          / DEC
        )*
        '''
        verifyChildren(node, "PrimaryExpression", None)
        self.visit(node.children[0])
        postfixes = node.children[1]
        for postfix in postfixes.children:
            first = postfix.children[0]
            if first.expr_name == "INC":
                verifyChildren(postfix, "INC")
                print("INC")
                #self.visit(postfix)
            elif first.expr_name == "DEC":
                verifyChildren(postfix, "DEC")
                print("DEC")
                #self.visit(postfix)
            else:
                assert(not postfix.expr_name)
                verifyChildren(postfix, None)
                postfix = postfix.children[0]
                first = postfix.children[0]
                if first.expr_name == "LBRK":
                    verifyChildren(postfix, "LBRK", "Expression", "RBRK")
                    self.visit(postfix.children[1])
                elif first.expr_name == "LPAR":
                    verifyChildren(postfix, "LPAR", None, "RPAR")
                    args_optional = postfix.children[1]
                    if len(args_optional.children) == 0:
                        pass
                    else:
                        verifyChildren(args_optional, "ArgumentExpressionList")
                        self.visit(args_optional.children[0])
                elif first.expr_name == "DOT":
                    verifyChildren(postfix, "DOT", "Identifier")
                elif first.expr_name == "PTR":
                    verifyChildren(postfix, "PTR", "Identifier")
                # TODO: handle the function call case
                else:
                    assert(False)

    def visitArgumentExpressionList(self, node):
        # ArgumentExpressionList = AssignmentExpression (COMMA AssignmentExpression)*
        verifyChildren(node, "AssignmentExpression", None)
        self.visit(node.children[0])
        node = node.children[1]
        for arg in node.children:
            verifyChildren(arg, "COMMA", "AssignmentExpression")
            self.visit(arg.children[1])

    def visitPrimaryExpression(self, node):
        # PrimaryExpression = StringLiteral / Constant / Identifier / ( LPAR Expression RPAR )
        verifyChildren(node, None)
        node = node.children[0]
        if node.expr_name in ["StringLiteral", "Constant", "PreprocessorDefined", "Identifier"]:
            self.visit(node)
        else:
            verifyChildren(node, "LPAR", "Expression", "RPAR")
            self.visit(node.children[1])
    def visitStringLiteral(self, node):
        s = toProcessedString(node)
        print("visit StringLiteral: {}".format(s))
    def visitIdentifier(self, node):
        # Identifier = !Keyword IdNondigit IdChar* Spacing
        verifyChildren(node, None, "IdNondigit", None, "Spacing")
        id = node.children[1].text + node.children[2].text
        print("visit Identifier: {}".format(id))
    def visitConstant(self, node):
        print("visit Constant: {}".format(node.text))
    def visitPreprocessorDefined(self, node):
        # PreprocessorDefined = (DEFINED LPAR DefinedArg RPAR) / (DEFINED DefinedArg)
        verifyChildren(node, None)
        node = node.children[0]
        if node.children[1].expr_name == "DefinedArg":
            verifyChildren(node, "DEFINED", "DefinedArg")
        else:
            verifyChildren(node, "DEFINED", "LPAR", "DefinedArg", "RPAR")
