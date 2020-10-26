#!/usr/bin/env python3
#
# Microsoft describes the pipeline to process C/C++ files here:
# https://docs.microsoft.com/en-us/cpp/preprocessor/phases-of-translation?view=vs-2019
#
# C Lexical Grammar: https://docs.microsoft.com/en-us/cpp/c-language/lexical-grammar?view=vs-2019
#
# Microsoft Preprocessor: https://docs.microsoft.com/en-us/cpp/preprocessor/preprocessor?view=vs-2019
#
# C/C++ Lexical Reference: https://docs.microsoft.com/en-us/cpp/cpp/lexical-conventions?view=vs-2019
# Preprocessor Reference: https://docs.microsoft.com/en-us/cpp/preprocessor/grammar-summary-c-cpp?view=vs-2019
#

# C/C++ Grammar: https://docs.microsoft.com/en-us/cpp/parallel/openmp/c-openmp-c-and-cpp-grammar?view=vs-2019
#
import os
import sys
import re

import errors
import stringreader
import preprocesslex
import preprocessparse

def findFileIgnoreCase(path, parts):
    #print("findFileIgnoreCase '{}' {}".format(path, parts))
    if len(parts) == 0:
        return path
    next_lower = parts[0].lower()
    for entry in os.listdir(path):
        if entry.lower() == next_lower:
            return findFileIgnoreCase(os.path.join(path, entry), parts[1:])
    return None

def findInclude(include_dirs, sub_path):
    sub_path_parts = None
    for include_dir in include_dirs:
        search_filename = os.path.join(include_dir, sub_path)
        if os.path.exists(search_filename):
            return include_dir, search_filename
        if os.name != 'nt':
            if not sub_path_parts:
                sub_path_parts = sub_path.split('/')
            filename = findFileIgnoreCase(include_dir, sub_path_parts)
            if filename:
                return include_dir, filename
    return None, None

def printNoInclude(include_dirs, sub_path):
    print("cannot find include '{}' in any of the following {} directories:".format(sub_path, len(include_dirs)), file=sys.stderr)
    index = 0
    for include_dir in include_dirs:
        print("  [{}] {}".format(index, include_dir), file=sys.stderr)
        index += 1

INDENT_STRING = '|' * 8
def printIndent(count):
    while count > len(INDENT_STRING):
        print(INDENT_STRING, end='')
        count -= len(INDENT_STRING)
    print(INDENT_STRING[:count], end='')

class DefineState:
    def __init__(self, id):
        self.id = id

class Condition:
    def __init__(self, parent, depth, node, enabled):
        self.parent = parent
        self.depth = depth
        self.node = node
        self.enabled = enabled
        self.defines = {}
    def get_is_defined(self, id):
        if id in self.defines:
            return True
        if self.depth == 0:
            return False
        return self.parent.get_is_defined(id)

class PreprocessFileData:
    def __init__(self, filename, src, nodes):
        self.filename = filename
        self.src = src
        self.nodes = nodes

class Preprocessor:
    def __init__(self, include_dirs, filename, src, nodes, **kwargs):
        self.include_dirs = include_dirs
        self.file_data = PreprocessFileData(filename, src, nodes)
        self.ignore_includes =  kwargs.get('ignore_includes', False)
        self.condition = Condition(None, 0, None, True)
    def fileLocationAtToken(self, token):
        lineno, col = errors.getLineAndCol(self.file_data.src[:token.start])
        return "{}({}:{}) ".format(self.file_data.filename, lineno, col)
    def pushNode(self, node, enabled):
        self.condition = Condition(self.condition, self.condition.depth + 1, node, enabled)
    def popNode(self):
        if self.condition.depth == 0:
            sys.exit("too many endifs")
        condition = self.condition
        self.condition = self.condition.parent
        return condition
    def printPrefixWithDepth(self, depth):
        printIndent(depth)
        if not self.condition.enabled:
            print("[DISABLED] ", end='')
    def printPrefix(self):
        self.printPrefixWithDepth(self.condition.depth)

    def go(self):
        depth_at_entry = self.condition.depth
        node_index = 0
        while True:
            if node_index == len(self.file_data.nodes):
                break
            node = self.file_data.nodes[node_index]
            node_index += 1
            if isinstance(node, preprocessparse.IncludeNode):
                self.printPrefix()
                print(node.desc(self.file_data.src))
                if self.condition.enabled:
                    include_dir, include_filename = findInclude(self.include_dirs, node.filename)
                    if not include_dir:
                        print(self.fileLocationAtToken(node.token), end='', file=sys.stderr)
                        printNoInclude(self.include_dirs, node.filename)
                        sys.exit(1)
                    if self.ignore_includes:
                        self.printPrefix()
                        print("ignore_includes is enabled, ignoring '{}'".format(include_filename))
                    else:
                        with open(include_filename, "r") as file:
                            include_src = file.read()
                        nodes = parse_text(include_filename, include_src)
                        parent_file_data = self.file_data
                        self.file_data = PreprocessFileData(include_filename, include_src, nodes)
                        try:
                            self.printPrefix()
                            print("--------------------------------------------------------------------------------")
                            self.printPrefix()
                            print("START FILE:{}".format(include_filename))
                            self.printPrefix()
                            print("--------------------------------------------------------------------------------")
                            self.go()
                            self.printPrefix()
                            print("--------------------------------------------------------------------------------")
                            self.printPrefix()
                            print("END FILE:{}".format(include_filename))
                            self.printPrefix()
                            print("--------------------------------------------------------------------------------")
                        finally:
                            self.file_data = parent_file_data

            elif isinstance(node, preprocessparse.DefineNode):
                self.printPrefix()
                print("define {}".format(node.desc(self.file_data.src)))
                if self.condition.enabled:
                    self.condition.defines[node.id] = DefineState(node.id)
            elif isinstance(node, preprocessparse.IfdefNode):
                self.printPrefix()
                print("if{}def '{}'".format("n" if node.is_not else "", node.id))
                if not self.condition.enabled:
                    enable_block = False
                else:
                    is_defined = self.condition.get_is_defined(node.id)
                    enable_block = (not is_defined) if node.is_not else is_defined
                self.pushNode(node, enable_block)
            elif isinstance(node, preprocessparse.IfNode):
                self.printPrefix()
                print("if {} '{}'".format(type(node.expression_node).__name__,
                                          " ".join([self.file_data.src[t.start:t.end] for t in node.condition_tokens])))
                if not self.condition.enabled:
                    enable_block = False
                else:
                    # TODO: implement logic to calculate enable_block
                    enable_block = False
                self.pushNode(node, enable_block)
            elif isinstance(node, preprocessparse.EndifNode):
                cond = self.popNode()
                self.printPrefix()
                print("endif: {}".format(cond.node.desc(self.file_data.src)))
            elif isinstance(node, preprocessparse.ElseNode):
                if self.condition.depth == 0:
                    sys.exit("else without an if?")
                self.printPrefixWithDepth(self.condition.depth - 1)
                print("else")
            else:
                # comment these out to make things faster for now
                pass
                #self.printPrefix()
                #print("TODO: process node {}".format(node.desc(self.file_data.src)))

        if self.condition.depth != depth_at_entry:
            sys.exit("need {} more endifs".format(self.condition.depth))

def parse_text(filename, src):
    parser = preprocessparse.Parser(preprocesslex.Lexer(stringreader.StringReader(src, filename)))
    nodes = []
    try:
        parser.parseInto(nodes)
    except preprocesslex.SyntaxError as syntax_error:
        sys.exit(syntax_error)
    return nodes

def process_text(include_dirs, filename, src, **kwargs):
    preprocessor = Preprocessor(include_dirs, filename, src, parse_text(filename, src), **kwargs)
    preprocessor.go()

def process_file(include_dirs, filename, **kwargs):
    with open(filename, "r") as file:
        src = file.read()
    process_text( include_dirs, filename, src, **kwargs)

def process_include(include_dirs, include_filename, **kwargs):
    include_dir, actual_filename = findInclude(include_dirs, include_filename)
    if not include_dir:
        printNoInclude(include_dirs, include_filename)
        sys.exit(1)
    return process_file(include_dirs, actual_filename, **kwargs)

def test_headers_in(include_dirs, dir, file_limit, **kwargs):
    file_count = 0
    print("[TEST] searching for headers in '{}':".format(dir))
    for entry in os.listdir(dir):
        if file_count == file_limit:
            print("[TEST] reached file limit of '{}'".format(file_limit))
            return
        if not entry.endswith(".h"):
            continue
        print("[TEST] lexing file '{}'".format(entry))
        process_file(include_dirs, os.path.join(dir, entry), **kwargs)
        file_count += 1


def testPreprocess(src):
    import inspect
    filename = "{}:{}".format(__file__, inspect.currentframe().f_back.f_lineno)
    nodes = process_text(None, filename, src)

def runTests():
    testPreprocess('#if a\n#endif')
    #testPreprocess('#if (a)\n#endif')
    testPreprocess('#if a && b\n#endif')
    testPreprocess('#if a && b\n#endif')
    testPreprocess('#if a && b && c\n#endif')
    testPreprocess('#if defined a\n#endif')
    testPreprocess('#if defined(a)\n#endif')
    testPreprocess('#if defined(a) && b\n#endif')
    #testPreprocess('#if defined (_MSC_VER) && (_MSC_VER >= 1020)')

def main():
    runTests()
    include_dirs = [
        "include",
        "10.0.17763.0/shared",
        "10.0.17763.0/um",
        "10.0.17763.0/ucrt",
        "10.0.17763.0/winrt",
    ]
    cmd_args = sys.argv[1:]
    if len(cmd_args) == 0:
        process_include(include_dirs, "Windows.h")
    else:
        test_headers_in(include_dirs, cmd_args[0], 999, ignore_includes=True)

    #test_headers_in(include_dirs, "include", 999, ignore_includes=True)
    #test_headers_in(include_dirs, "10.0.17763.0/shared", 999, ignore_includes=True)
    #test_headers_in(include_dirs, "10.0.17763.0/um", 999, ignore_includes=True)
    #test_headers_in(include_dirs, "10.0.17763.0/ucrt", 999, ignore_includes=True)

main()
