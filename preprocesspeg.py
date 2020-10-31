import os
import sys
import parsimoniousdeps
import parsimonious

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_SCRIPT_DIR, "commontokens.peg")) as file:
    commontokens_peg = file.read()
with open(os.path.join(_SCRIPT_DIR, "preprocessor.peg")) as file:
    preprocessor_peg = file.read()
GRAMMAR = parsimonious.Grammar(preprocessor_peg + commontokens_peg)
