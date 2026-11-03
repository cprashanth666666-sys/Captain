cells = []


def md(text):
    cells.append(("markdown", text.strip("\n")))


def code(text):
    cells.append(("code", text.strip("\n")))
