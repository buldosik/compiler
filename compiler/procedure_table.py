from code_generator import CodeGenerator

class ProcedureTable(dict):
    def __init__(self, memory_offset):
        super().__init__()
        self.memory_offset = memory_offset
        self.current_line = 0
        self.first_line = []
        self.code = []

    def add_procedure(self, procedure):
        if procedure.name in self:
            raise Exception(f"Redeclaration of {procedure.name}")
        self.setdefault(procedure.name, procedure)
        self.memory_offset = procedure.last_indeks

    def pre_gen_const(self):
        self.first_line.append(f"SET 0")
        self.first_line.append(f"STORE 10 #Store 0")
        self.first_line.append(f"SET 1")
        self.first_line.append(f"STORE 11 #Store 1")
        self.current_line += 4

    def gen_first_jump(self):
        self.first_line.append(f"JUMP start_program")
        #print(self.first_line)
        self.current_line += 1

    def update_first_jump(self):
        first_line = self["PROGRAM"].first_line
        self.first_line[4] = self.first_line[4].replace('start_program', str(first_line - 4))

    def gen_code(self):
        codeGenerator = CodeGenerator()
        for name in self:
            self[name].first_line = self.current_line
            #print('NAME:::::::::::::::', name, self.current_line, self[name].memory_offset)
            codeGenerator.gen_code_from_procedure(name, self)
            self.code.append(codeGenerator.code)
            self.current_line += len(codeGenerator.code)
