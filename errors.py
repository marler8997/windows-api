def getLineAndCol(str):
    lineno = 1 + str.count("\n")
    lastnewline = str.rfind("\n")
    if lastnewline == -1:
            lastnewline = 0
    return lineno, len(str) - lastnewline + 1
