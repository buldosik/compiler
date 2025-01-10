debug = False
debug_compiler_depth = 1
# 0 - nothing
# 1 - new part
# 2 - +old part
# 3 - +all tokenized
debug_code_depth = 1

isStrict = False

def log_compiler(depth, info):
    if depth <= debug_compiler_depth:
        print(info)

        
def log_code(depth, info):
    if depth <= debug_code_depth:
        print(info)