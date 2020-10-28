import os
import sys
import parsimoniousdeps
import parsimonious

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_SCRIPT_DIR, "cexpr.peg")) as file:
    cexpr_peg = file.read()
GRAMMAR = parsimonious.Grammar(cexpr_peg)
