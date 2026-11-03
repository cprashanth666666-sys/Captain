import sys, importlib, nbformat as nbf
import nb_helpers
parts = sys.argv[2:]
for p in parts: importlib.import_module(p)
nb = nbf.v4.new_notebook()
nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
nb.cells = [nbf.v4.new_markdown_cell(t) if k == "markdown" else nbf.v4.new_code_cell(t) for k, t in nb_helpers.cells]
nbf.write(nb, sys.argv[1])
print(len(nb.cells), "cells")
