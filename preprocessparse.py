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
        expr = visitor.visit(expr_node)
        assert(expr)
        #expr.eval(None)
        return expr

class Expression:
    def eval(self, state):
        #raise Exception("{}.eval not implemented".format(type(self).__name__))
        print("TODO: {}.eval not implemented".format(type(self).__name__))
        return 0
class BinaryExpression(Expression):
    def __init__(self, op_token, expr1, expr2):
        self.op_token = op_token
        self.expr1 = expr1
        self.expr2 = expr2
class UnaryExpression(Expression):
    def __init__(self, op_token, expr):
        self.op_token = op_token
        self.expr = expr
class CallExpression(Expression):
    def __init__(self, func_expr, args):
        self.func_expr = func_expr
        self.args = args
class IndexExpression(Expression):
    def __init__(self, array_expr, index_expr):
        self.array_expr = array_expr
        self.index_expr = index_expr
class DotMemberExpression(Expression):
    def __init__(self, obj_expr, member):
        self.obj_expr = obj_expr
        self.member = member
class PtrMemberExpression(Expression):
    def __init__(self, obj_expr, member):
        self.obj_expr = obj_expr
        self.member = member
class NumberExpression(Expression):
    def __init__(self, number_token):
        self.number_token = number_token
class StringExpression(Expression):
    def __init__(self, string_node, value):
        self.string_node = string_node
        self.value = value
class IdentifierExpression(Expression):
    def __init__(self, id_node, id):
        self.id_node = id_node
        self.id = id
class DefinedExpression(Expression):
    def __init__(self, id_node, id):
        self.id_node = id_node
        self.id = id
    #def eval(self, state):
    #    return 1 if state.condition.get_is_defined(self.id) else 0
class ConstantExpression(Expression):
    def __init__(self, node, string_value):
        self.node = node
        self.string_value = string_value

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
        expr = self.visit(node.children[0])
        if not isEmpty(node.children[1]):
            sys.exit("not impl")
        return expr
    def visitAssignmentExpression(self, node):
        if node.children[0].expr_name == "ConditionalExpression":
            verifyChildren(node, "ConditionalExpression")
            return self.visit(node.children[0])
        else:
            sys.exit("not impl assign expr")
    def visitConditionalExpression(self, node):
        verifyChildren(node, "LogicalORExpression", None)
        expr = self.visit(node.children[0])
        if not isEmpty(node.children[1]):
            sys.exit("not impl conditional expr")
        return expr

    def visitBinaryExpression(self, node, op_expr_names, next_expr_name):
        # SomeBinaryExpression = NextBinaryExpression (OP NextBinaryExpression)*
        verifyChildren(node, next_expr_name, None)
        expr = self.visit(node.children[0])
        node = node.children[1]
        for node in node.children:
            verifyChildren(node, None, next_expr_name)
            if len(op_expr_names) == 1:
                op_node = node.children[0]
            else:
                verifyChildren(node.children[0], None)
                op_node = node.children[0].children[0]
            assert(op_node.expr_name in op_expr_names)
            next_expr = self.visit(node.children[1])
            expr = BinaryExpression(op_node, expr, next_expr)
        return expr
    def visitLogicalORExpression(self, node):
        return self.visitBinaryExpression(node, ("OROR",), "LogicalANDExpression")
    def visitLogicalANDExpression(self, node):
        return self.visitBinaryExpression(node, ("ANDAND",), "InclusiveORExpression")
    def visitInclusiveORExpression(self, node):
        return self.visitBinaryExpression(node, ("OR",), "ExclusiveORExpression")
    def visitExclusiveORExpression(self, node):
        return self.visitBinaryExpression(node, ("HAT",), "ANDExpression")
    def visitANDExpression(self, node):
        return self.visitBinaryExpression(node, ("AND",), "EqualityExpression")
    def visitEqualityExpression(self, node):
        return self.visitBinaryExpression(node, ("EQUEQU","BANGEQU"), "RelationalExpression")
    def visitRelationalExpression(self, node):
        return self.visitBinaryExpression(node, ("LE", "GE", "LT", "GT"), "ShiftExpression")
    def visitShiftExpression(self, node):
        return self.visitBinaryExpression(node, ("LEFT", "RIGHT"), "AdditiveExpression")
    def visitAdditiveExpression(self, node):
        return self.visitBinaryExpression(node, ("PLUS", "MINUS"), "MultiplicativeExpression")
    def visitMultiplicativeExpression(self, node):
        return self.visitBinaryExpression(node, ("STAR", "DIV", "MOD"), "CastExpression")

    def visitUnaryExpression(self, node):
        # TODO: support sizeof?
        # UnaryExpression = PostfixExpression / (INC UnaryExpression) / (DEC UnaryExpression) / (UnaryOperator CastExpression)
        verifyChildren(node, None)
        node = node.children[0]
        if node.expr_name == "PostfixExpression":
            return self.visit(node)

        assert(not node.expr_name)
        first = node.children[0]
        if first.expr_name == "INC":
            verifyChildren(node, "INC", "UnaryExpression")
            return UnaryExpression(node.children[0], self.visit(node.children[1]))
        if first.expr_name == "DEC":
            verifyChildren(node, "DEC", "UnaryExpression")
            return UnaryExpression(node.children[0], self.visit(node.children[1]))
        if first.expr_name == "UnaryOperator":
            verifyChildren(node, "UnaryOperator", "CastExpression")
            return UnaryExpression(node.children[0], self.visit(node.children[1]))
        assert(False)

    def visitCastExpression(self, node):
        verifyChildren(node, "UnaryExpression")
        return self.visit(node.children[0])

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
        expr = self.visit(node.children[0])
        node = node.children[1]
        for node in node.children:
            first = node.children[0]
            if first.expr_name == "INC" or first.expr_name == "DEC":
                verifyChildren(node, None)
                expr = UnaryExpression(node, expr)
                continue

            assert(not node.expr_name)
            verifyChildren(node, None)
            node = node.children[0]
            first = node.children[0]
            if first.expr_name == "LBRK":
                verifyChildren(node, "LBRK", "Expression", "RBRK")
                expr = IndexExpression(expr, self.visit(node.children[1]))
            elif first.expr_name == "LPAR":
                verifyChildren(node, "LPAR", None, "RPAR")
                args_optional = node.children[1]
                if len(args_optional.children) == 0:
                    expr = CallExpression(expr, [])
                else:
                    verifyChildren(args_optional, "ArgumentExpressionList")
                    expr = CallExpression(expr, self.parseArgumentExpressionList(args_optional.children[0]))
            elif first.expr_name == "DOT":
                verifyChildren(node, "DOT", "Identifier")
                expr = DotMemberExpression(expr, node.children[1])
            elif first.expr_name == "PTR":
                verifyChildren(node, "PTR", "Identifier")
                expr = PtrMemberExpression(expr, node.children[1])
            else:
                assert(False)
        return expr

    def parseArgumentExpressionList(self, node):
        # ArgumentExpressionList = AssignmentExpression (COMMA AssignmentExpression)*
        verifyChildren(node, "AssignmentExpression", None)
        args = [self.visit(node.children[0])]
        node = node.children[1]
        for arg in node.children:
            verifyChildren(arg, "COMMA", "AssignmentExpression")
            args.append(self.visit(arg.children[1]))
        return args

    def visitPrimaryExpression(self, node):
        # PrimaryExpression = StringLiteral / Constant / Identifier / ( LPAR Expression RPAR )
        verifyChildren(node, None)
        node = node.children[0]
        if node.expr_name in ["StringLiteral", "Constant", "PreprocessorDefined", "Identifier"]:
            return self.visit(node)
        else:
            verifyChildren(node, "LPAR", "Expression", "RPAR")
            return self.visit(node.children[1])
    def visitStringLiteral(self, node):
        value = toProcessedString(node)
        return StringExpression(node, value)
    def visitIdentifier(self, node):
        # Identifier = !Keyword IdNondigit IdChar* Spacing
        verifyChildren(node, None, "IdNondigit", None, "Spacing")
        id = node.children[1].text + node.children[2].text
        return IdentifierExpression(node, id)
    def visitConstant(self, node):
        return ConstantExpression(node, node.text)
    def visitPreprocessorDefined(self, node):
        # PreprocessorDefined = (DEFINED LPAR DefinedArg RPAR) / (DEFINED DefinedArg)
        verifyChildren(node, None)
        node = node.children[0]
        if node.children[1].expr_name == "DefinedArg":
            verifyChildren(node, "DEFINED", "DefinedArg")
            return DefinedExpression(node.children[1], node.children[1].text)
        else:
            verifyChildren(node, "DEFINED", "LPAR", "DefinedArg", "RPAR")
            return DefinedExpression(node.children[2], node.children[2].text)
