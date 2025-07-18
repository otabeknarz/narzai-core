code = input()

i = 0
iterations = len(code) + code.count("{") + code.count("}")
while i < iterations:
    if "{" == code[i]: 
        code = code[:i+1] + "{" + code[i+1:]; i += 1
    elif "}" == code[i]:
        code = code[:i+1] + "}" + code[i+1:]; i += 1
    i += 1
print("Codebase:", code)