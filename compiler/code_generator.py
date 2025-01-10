from procedure import Array, Link, Link_T, Variable
from config import debug, isStrict

address_reg = 'f'
value_reg = 'g'
r_a = 'a'

class CodeGenerator:
    def __init__(self):
        self.first_line = 0
        self.commands = []
        self.symbols = {}
        self.links = {}
        self.code = []
    
    def get_current_line(self, withOffset=True):
        if withOffset:
            return self.first_line + len(self.code)
        else:
            return len(self.code)
    
    def replace_line_with(self, text_to_replace, text, fisrt_index, last_index):
        for i in range(fisrt_index, last_index):
            self.code[i] = self.code[i].replace(text_to_replace, text)

    def gen_code_from_procedure(self, name, procedure_table):
        if debug:
            print(name)
        self.loop_depth = 0
        self.procedure_table = procedure_table
        self.procedure = procedure_table[name]
        self.commands = self.procedure.commands
        self.symbols = self.procedure.symbols
        self.links = self.procedure.links
        self.code = []
        self.first_line = procedure_table.current_line
        self.gen_code_from_commands(self.commands)
        if name == 'PROGRAM':
            self.code.append("HALT")
        else:
            self.gen_proc_jump_back(self.procedure.memory_offset)

    def gen_proc_jump_back(self, memory_offset):
        self.gen_const(memory_offset, r_a)
        self.code.append(f"LOAD {r_a}")
        self.code.append(f"JUMPR {r_a} # BACK")

    def gen_code_from_commands(self, commands):
        for command in commands:
            match command[0]:
                case "write":
                    self.command_write(command)
                case "read":
                    self.command_read(command)
                case "assign":
                    self.command_assign(command)
                case "if":
                    self.command_if(command)
                case "ifelse":
                    self.command_ifelse(command)
                case "while":
                    self.command_while(command)
                case "until":
                    self.command_until(command)
                case "proc_call":
                    self.command_proc_call(command)
                case _:
                    raise Exception("Not declared command")
    
#region Command

    def command_write(self, command):
        if debug:
            print("Write")
        value = command[1]

        if value[0] == "load":
            self.default_load_var(value[1], out_reg='a')

        elif value[0] == "const":
            self.gen_const(value[1], reg='a')

        self.code.append(f"WRITE")

    def command_read(self, command):
        if debug:
            print("read")
        target = command[1]

        self.default_load_address(target, isInitialising=True)

        self.code.append(f"READ")
        self.code.append(f"STORE {address_reg}")

    def command_assign(self, command):
        if debug:
            print("assign")
        target = command[1]

        expression = command[2]
        self.calculate_expression(expression, value_reg)

        self.default_load_address(target, isInitialising=True)
            
        self.code.append(f"GET {value_reg}")
        self.code.append(f"STORE {address_reg}")

    def command_if(self, command):
        if debug:
            print("if")
        condition = self.simplify_condition(command[1])
        if isinstance(condition, bool):
            if condition:
                self.gen_code_from_commands(command[2])
        else:
            condition_start = self.get_current_line(withOffset=False)
            self.check_condition(condition, "if_finish")

            command_start = self.get_current_line(withOffset=False)
            self.gen_code_from_commands(command[2])
            
            command_end = self.get_current_line()
            self.replace_line_with("if_finish", str(command_end) + " # endif", condition_start, command_start)

    def command_ifelse(self, command):
        if debug:
            print("ifelse")
        condition = self.simplify_condition(command[1])
        if isinstance(condition, bool):
            if condition:
                self.gen_code_from_commands(command[2])
            else:
                self.gen_code_from_commands(command[3])
        else:
            condition_start = self.get_current_line(withOffset=False)
            self.check_condition(command[1], 'else_start')

            if_start = self.get_current_line(withOffset=False)
            self.gen_code_from_commands(command[2])

            self.code.append(f"JUMP endif")

            else_start = self.get_current_line()
            else_start_local = self.get_current_line(withOffset=False)
            self.gen_code_from_commands(command[3])

            command_end = self.get_current_line()

            self.replace_line_with("else_start", str(else_start) + " # else_start", condition_start, if_start)
            self.replace_line_with("endif", str(command_end) + " # endif", else_start_local-1, else_start_local)
            #print(self.code[else_start-1])
            #self.code[else_start-1] = self.code[else_start-1].replace('finish',str(command_end))
            #for i in range(condition_start, if_start):
            #    self.code[i] = self.code[i].replace('finish', str(else_start))

    def command_while(self, command):
        if debug:
            print("while")
        condition = self.simplify_condition(command[1])
        if isinstance(condition, bool):
            if condition:
                #infinity loop
                loop_start = self.get_current_line()
                self.gen_code_from_commands(command[2])
                self.code.append(f"JUMP {loop_start}")
        else:
            condition_start_local = self.get_current_line(withOffset=False)
            condition_start = self.get_current_line()
            self.check_condition(command[1], 'while_end')

            loop_start = self.get_current_line(withOffset=False)
            self.loop_depth += 1
            self.gen_code_from_commands(command[2])
            self.loop_depth -= 1

            self.code.append(f"JUMP {condition_start} # while condition")

            loop_end = self.get_current_line()

            self.replace_line_with("while_end", str(loop_end) + " # while_end", condition_start_local, loop_start)

    def command_until(self, command):
        if debug:
            print("until")
        loop_start = self.get_current_line()
        self.loop_depth += 1
        self.gen_code_from_commands(command[2])
        self.loop_depth -= 1

        condition_start = self.get_current_line(withOffset=False)
        self.check_condition(command[1], 'loop_start')

        condition_end = self.get_current_line(withOffset=False)
        self.replace_line_with("loop_start", str(loop_start) + " # loop_start", condition_start, condition_end)

    def command_proc_call(self, command, address_reg='e'):
        if debug:
            print("proc_call")
        proc_call = command[1]
        proc_call_name = proc_call[0]
        proc_call_variables = proc_call[1]
        if proc_call_name not in self.procedure_table:
            raise Exception(f"Trying to call undeclared procedure {proc_call_name}")
        proc = self.procedure_table[proc_call_name]
        proc_offset = proc.memory_offset
        current_offset = proc_offset + 1

        # Load and store addresses
        for variable in proc_call_variables:
            self.gen_const(current_offset, r_a)
            self.code.append(f"PUT {address_reg}")

            if variable[0] == "load":
                self.default_load_address(variable[1], out_reg='a')
                name, link = proc.get_link_by_offset(current_offset)
                # Type Check
                typeOfLink = 'Array' if type(link) == Link_T else 'Var'
                if variable[1] in self.symbols:
                    typeOfVar = 'Array' if type(self.symbols[variable[1]]) == Array else 'Var'
                elif variable[1] in self.links:
                    typeOfVar = 'Array' if type(self.links[variable[1]]) == Link_T else 'Var'
                else:
                    raise Exception(f"Variable {variable[1]} is not declared")
                
                if typeOfLink != typeOfVar:
                    raise Exception(f"Wrong type of {current_offset - proc_offset} argument, when you try to call {proc_call_name}")
                
                # Initilized check & update
                
                if typeOfLink == 'Var' and link.isInitialized:
                    if variable[1] in self.symbols:
                        self.symbols[variable[1]].isInitialized = link.isInitialized
                    elif variable[1] in self.links:
                        self.links[variable[1]].isInitialized = link.isInitialized

                # if variable[1] in self.symbols:
                #     proc.get_link(variable[1]).isInitialized = self.symbols[variable[1]]
                # elif variable[1] in self.links:
                #     proc.get_link(variable[1]).isInitialized = self.links[variable[1]]
            else:
                raise Exception("Command_proc_call Error")
            
            self.code.append(f"STORE {address_reg}")
            
            current_offset += 1
        
        # Store return line
        self.gen_const(4, reg='b')
        self.gen_const(proc_offset, reg='a')
        self.code.append(f"PUT {address_reg}")
        self.code.append(f"STRK {r_a}")
        self.code.append(f"ADD b")
        self.code.append(f"STORE {address_reg}")
        
        # Jump
        self.code.append(f"JUMP {proc.first_line}")

#endregion
    
    def gen_const(self, const, reg='h'):
        self.code.append(f"RST {reg}")
        if const > 0:
            bits = bin(const)[2:]
            for bit in bits[:-1]:
                if bit == '1':
                    self.code.append(f"INC {reg}")
                self.code.append(f"SHL {reg}")
            if bits[-1] == '1':
                self.code.append(f"INC {reg}")

#region calculate_expression
                
    def calculate_expression(self, expression, out_reg='a'):
        match expression[0]:
            case "const":
                self.gen_const(expression[1], out_reg)
            case "load":
                self.default_load_var(expression[1], out_reg)
            case _:
                if expression[0] == "add":
                    if expression[1][0] == 'const' and expression[2][0] != 'const':
                        expression = (expression[0], expression[2], expression[1])
                    self.calculate_add(expression[1], expression[2], out_reg)

                elif expression[0] == "sub":
                    self.calclate_sub(expression[1], expression[2], out_reg)

                elif expression[0] == "mul":
                    if expression[1][0] == 'const' and expression[2][0] != 'const':
                        expression = (expression[0], expression[2], expression[1])
                    self.calculate_mul(expression[1], expression[2], out_reg)

                elif expression[0] == "div":
                    self.calculate_div(expression[1], expression[2], out_reg)

                elif expression[0] == "mod":
                    self.calculate_mod(expression[1], expression[2], out_reg)

    def calculate_add(self, expression1, expression2, out_reg='a', second_reg='b'):
        if expression1[0] == expression2[0] == "const":
            self.gen_const(expression1[1] + expression2[1], out_reg)

        elif expression1 == expression2:
            self.calculate_expression(expression1, out_reg)
            self.code.append(f"SHL {out_reg}")
        
        elif expression2[0] == "const" and expression2[1] < 12:
            self.calculate_expression(expression1, out_reg)
            change = f"INC {out_reg}"
            self.code += expression2[1] * [change]

        else:
            self.calculate_expression(expression1, out_reg)
            self.calculate_expression(expression2, second_reg)
            if out_reg != 'a':
                self.code.append(f"GET {out_reg}")
            self.code.append(f"ADD {second_reg}")
            if out_reg != 'a':
                self.code.append(f"PUT {out_reg}")

    def calclate_sub(self, expression1, expression2, out_reg='a', second_reg='b'):
        if expression1[0] == expression2[0] == "const":
            val = max(0, expression1[1] - expression2[1])
            if val:
                self.gen_const(val, out_reg)
            else:
                self.code.append(f"RST {out_reg}")

        elif expression1 == expression2:
            self.code.append(f"RST {out_reg}")

        elif expression2[0] == "const" and expression2[1] < 12:
            self.calculate_expression(expression1, out_reg)
            change = f"DEC {out_reg}"
            self.code += expression2[1] * [change]

        else:
            self.calculate_expression(expression1, out_reg)
            self.calculate_expression(expression2, second_reg)
            if out_reg != 'a':
                self.code.append(f"GET {out_reg}")
            self.code.append(f"SUB {second_reg}")
            if out_reg != 'a':
                self.code.append(f"PUT {out_reg}")

    def calculate_mul(self, expression1, expression2, out_reg='a', second_reg='b', third_reg='c', temp_res_reg='d'):
        if expression1[0] == expression2[0] == "const":
            self.gen_const(expression1[1] * expression2[1], out_reg)
            return

        if expression2[0] == "const":
            val = expression2[1]
            if val == 0:
                self.code.append(f"RST {out_reg}")
                return
            elif val == 1:
                self.calculate_expression(expression1, out_reg)
                return
            elif val & (val - 1) == 0:
                self.calculate_expression(expression1, out_reg)
                while val > 1:
                    self.code.append(f"SHL {out_reg}")
                    val /= 2
                return

        if expression1 == expression2:
            self.calculate_expression(expression1, second_reg)
            self.code.append(f"RST {r_a}")
            self.code.append(f"ADD {second_reg}")
            self.code.append(f"PUT {third_reg}")
        else:
            self.calculate_expression(expression1, second_reg)
            self.calculate_expression(expression2, third_reg)

        first_line = self.get_current_line() - 1

        self.code.append(f"RST {temp_res_reg}") #1
        self.code.append(f"GET {third_reg}")
        self.code.append(f"SUB {second_reg}")
        self.code.append(f"JPOS {first_line + 21}")
        self.code.append(f"JUMP {first_line + 8}")

        # if second >= third it's better to do $2 * $3

        self.code.append(f"SHL {second_reg}") # 6
        self.code.append(f"SHR {third_reg}")

        self.code.append(f"GET {third_reg}") # 8
        self.code.append(f"JZERO {first_line + 32}")
        self.code.append(f"SHR {third_reg}")
        self.code.append(f"SHL {third_reg}")
        self.code.append(f"SUB {third_reg}")
        self.code.append(f"JPOS {first_line + 15}")
        self.code.append(f"JUMP {first_line + 6}")

        self.code.append(f"GET {temp_res_reg}") # 15
        self.code.append(f"ADD {second_reg}")
        self.code.append(f"PUT {temp_res_reg}")
        self.code.append(f"JUMP {first_line + 6}")

        # if second <= third it's better to do $3 * $2

        self.code.append(f"SHL {third_reg}") # 19
        self.code.append(f"SHR {second_reg}")

        self.code.append(f"GET {second_reg}") # 21
        self.code.append(f"JZERO {first_line + 32}")
        self.code.append(f"SHR {second_reg}")
        self.code.append(f"SHL {second_reg}")
        self.code.append(f"SUB {second_reg}")
        self.code.append(f"JPOS {first_line + 28}")
        self.code.append(f"JUMP {first_line + 19}")

        self.code.append(f"GET {temp_res_reg}") # 28
        self.code.append(f"ADD {third_reg}")
        self.code.append(f"PUT {temp_res_reg}")
        self.code.append(f"JUMP {first_line + 19}") # 31

        if out_reg != temp_res_reg:
            self.code.append(f"GET {temp_res_reg}")
            self.code.append(f"PUT {out_reg}")

    def calculate_div(self, expression1, expression2, out_reg='a', second_reg='b', third_reg='c'):
        if expression1[0] == expression2[0] == "const":
            if expression2[1] > 0:
                self.gen_const(expression1[1] // expression2[1], out_reg)
            else:
                self.code.append(f"RST {out_reg}")
            return

        elif expression1[0] == "const" and expression1[1] == 0:
            self.code.append(f"RST {out_reg}")
            return
        
        elif expression1 == expression2:
            self.calculate_expression(expression1, second_reg)
            first_line = self.get_current_line()
            self.code.append(f"GET {second_reg}")
            self.code.append(f"JZERO {first_line + 5}")
            self.code.append(f"RST {out_reg}")
            self.code.append(f"INC {out_reg}")
            return

        elif expression2[0] == "const":
            val = expression2[1]
            if val == 0:
                self.code.append(f"RST {out_reg}")
                return
            elif val == 1:
                self.calculate_expression(expression1, out_reg)
                return
            elif val & (val - 1) == 0:
                self.calculate_expression(expression1, out_reg)
                while val > 1:
                    self.code.append(f"SHR {out_reg}")
                    val /= 2
                return

        self.calculate_expression(expression1, second_reg)
        self.calculate_expression(expression2, third_reg)
        self.perform_division(out_reg=out_reg, dividend_reg=second_reg, divisor_reg=third_reg)

    def calculate_mod(self, expression1, expression2, out_reg='a', second_reg='b', third_reg='c'):
        if expression1[0] == expression2[0] == "const":
            if expression2[1] > 0:
                self.gen_const(expression1[1] % expression2[1], out_reg)
            else:
                self.code.append(f"RST {out_reg}")
            return

        elif expression1 == expression2:
            self.code.append(f"RST {out_reg}")
            return

        elif expression1[0] == "const" and expression1[1] == 0:
            self.code.append(f"RST {out_reg}")
            return

        elif expression2[0] == "const":
            val = expression2[1]
            if val < 2:
                self.code.append(f"RST {out_reg}")
                return
            elif val == 2:
                self.calculate_expression(expression1, second_reg)
                self.code.append(f"GET {second_reg}")
                self.code.append(f"SHR {second_reg}")
                self.code.append(f"SHL {second_reg}")
                self.code.append(f"SUB {second_reg}")
                if out_reg != 'a':
                    self.code.append(f"PUT {out_reg}")
                return

        self.calculate_expression(expression1, second_reg)
        self.calculate_expression(expression2, third_reg)
        self.perform_division(out_mod_reg=out_reg, dividend_reg=second_reg, divisor_reg=third_reg)

    def perform_division(self, out_reg='d', out_mod_reg='e',
                         dividend_reg='b', divisor_reg='c',
                         quotient_reg='d', remainder_reg='e'):

        first_line = self.get_current_line() - 1
        self.code.append(f"RST {quotient_reg}")          # 1
        self.code.append(f"RST {remainder_reg}")
        self.code.append(f"GET {divisor_reg}")
        self.code.append(f"JZERO {first_line + 37}")     # Exit
        self.code.append(f"GET {dividend_reg}")          # 5
        self.code.append(f"PUT {remainder_reg}")
        self.code.append(f"GET {divisor_reg}")
        self.code.append(f"PUT {dividend_reg}")
        self.code.append(f"GET {remainder_reg}")
        self.code.append(f"SUB {dividend_reg}")
        self.code.append(f"JZERO {first_line + 19}")
        self.code.append(f"GET {dividend_reg}")          # 12
        self.code.append(f"SUB {remainder_reg}")
        self.code.append(f"JZERO {first_line + 17}")
        self.code.append(f"SHR {dividend_reg}")
        self.code.append(f"JUMP {first_line + 19}")
        self.code.append(f"SHL {dividend_reg}")          # 17
        self.code.append(f"JUMP {first_line + 12}")

        self.code.append(f"GET {dividend_reg}")          # 19
        self.code.append(f"SUB {remainder_reg}")
        self.code.append(f"JZERO {first_line + 23}")
        self.code.append(f"JUMP {first_line + 37}")      # Exit
        self.code.append(f"GET {remainder_reg}")         # 23
        self.code.append(f"SUB {dividend_reg}")
        self.code.append(f"PUT {remainder_reg}")
        self.code.append(f"INC {quotient_reg}")

        self.code.append(f"GET {dividend_reg}")          # 27
        self.code.append(f"SUB {remainder_reg}")
        self.code.append(f"JZERO {first_line + 19}")
        self.code.append(f"SHR {dividend_reg}")
        self.code.append(f"GET {divisor_reg}")
        self.code.append(f"SUB {dividend_reg}")
        self.code.append(f"JZERO {first_line + 35}")
        self.code.append(f"JUMP {first_line + 37}")
        self.code.append(f"SHL {quotient_reg}")          # 35
        self.code.append(f"JUMP {first_line + 27}")      # 36

        if out_reg != quotient_reg:
            self.code.append(f"GET {quotient_reg}")
            self.code.append(f"PUT {out_reg}")

        if out_mod_reg != remainder_reg:
            self.code.append(f"GET {remainder_reg}")
            self.code.append(f"PUT {out_mod_reg}")

#endregion

#region condition

    def simplify_condition(self, condition):
        if condition[1][0] == "const" and condition[2][0] == "const":
            if condition[0] == "le":
                return condition[1][1] <= condition[2][1]
            elif condition[0] == "ge":
                return condition[1][1] >= condition[2][1]
            elif condition[0] == "lt":
                return condition[1][1] < condition[2][1]
            elif condition[0] == "gt":
                return condition[1][1] > condition[2][1]
            elif condition[0] == "eq":
                return condition[1][1] == condition[2][1]
            elif condition[0] == "ne":
                return condition[1][1] != condition[2][1]

        elif condition[1][0] == "const" and condition[1][1] == 0:
            if condition[0] == "le":
                return True
            elif condition[0] == "gt":
                return False
            else:
                return condition

        elif condition[2][0] == "const" and condition[2][1] == 0:
            if condition[0] == "ge":
                return True
            elif condition[0] == "lt":
                return False
            else:
                return condition

        elif condition[1] == condition[2]:
            if condition[0] in ["ge", "le", "eq"]:
                return True
            else:
                return False

        else:
            return condition

    def check_condition(self, condition, exit_line='finish',out_reg='a', second_reg='b', third_reg='c'):
        if condition[1][0] == "const" and condition[1][1] == 0:
            if condition[0] == "ge" or condition[0] == "eq":
                self.calculate_expression(condition[2], r_a)
                current_line = self.get_current_line()
                self.code.append(f"JZERO {current_line + 2}")
                self.code.append(f"JUMP {exit_line}")

            elif condition[0] == "lt" or condition[0] == "ne":
                self.calculate_expression(condition[2], r_a)
                self.code.append(f"JZERO {exit_line}")

        elif condition[2][0] == "const" and condition[2][1] == 0:
            if condition[0] == "le" or condition[0] == "eq":
                self.calculate_expression(condition[1], r_a)
                current_line = self.get_current_line()
                self.code.append(f"JZERO {current_line + 2}")
                self.code.append(f"JUMP {exit_line}")

            elif condition[0] == "gt" or condition[0] == "ne":
                self.calculate_expression(condition[1], r_a)
                self.code.append(f"JZERO {exit_line}")

        else:
            self.calculate_expression(condition[1], second_reg)
            self.calculate_expression(condition[2], third_reg)

            if condition[0] == "le":
                self.code.append(f"GET {second_reg}")
                self.code.append(f"SUB {third_reg}")
                current_line = self.get_current_line()
                self.code.append(f"JZERO {current_line + 2}")
                self.code.append(f"JUMP {exit_line}")

            elif condition[0] == "ge":
                self.code.append(f"GET {third_reg}")
                self.code.append(f"SUB {second_reg}")
                current_line = self.get_current_line()
                self.code.append(f"JZERO {current_line + 2}")
                self.code.append(f"JUMP {exit_line}")

            elif condition[0] == "lt":
                self.code.append(f"GET {third_reg}")
                self.code.append(f"SUB {second_reg}")
                current_line = self.get_current_line()
                self.code.append(f"JPOS {current_line + 2}")
                self.code.append(f"JUMP {exit_line}")

            elif condition[0] == "gt":
                self.code.append(f"GET {second_reg}")
                self.code.append(f"SUB {third_reg}")
                current_line = self.get_current_line()
                self.code.append(f"JPOS {current_line + 2}")
                self.code.append(f"JUMP {exit_line}")

            elif condition[0] == "eq":
                self.code.append(f"GET {second_reg}")
                self.code.append(f"SUB {third_reg}")
                current_line = self.get_current_line()
                self.code.append(f"JZERO {current_line  + 2}")
                self.code.append(f"JUMP {exit_line}")

                self.code.append(f"GET {third_reg}")
                self.code.append(f"SUB {second_reg}")
                current_line = self.get_current_line()
                self.code.append(f"JZERO {current_line + 2}")
                self.code.append(f"JUMP {exit_line}")

            elif condition[0] == "ne":
                self.code.append(f"GET {second_reg}")
                self.code.append(f"SUB {third_reg}")
                current_line = self.get_current_line()
                self.code.append(f"JZERO {current_line  + 2}")
                self.code.append(f"JUMP {current_line + 5}")

                self.code.append(f"GET {third_reg}")
                self.code.append(f"SUB {second_reg}")
                current_line = self.get_current_line()
                self.code.append(f"JZERO {exit_line}")

#endregion

#region Load

    def default_load_var(self, target, out_reg=value_reg):
        if type(target) == tuple:
            if target[0] == "undeclared":
                raise Exception(f"Assigning to undeclared variable {target[1]}")
            elif target[0] == "array":
                self.load_array_at(target[1], target[2], out_reg)
            elif target[0] == "link_t":
                self.load_link_T_at(target[1], target[2], out_reg)
            else:
                raise Exception(f"default_load_var")
        else:
            if target in self.links and type(self.links[target]) == Link:
                self.load_link_variable(target, out_reg)
                self.links[target].isUsed = True
                # if self.links[target].isInitialized:
                #     self.load_link_variable(target, out_reg)
                # else:
                #     raise Exception(f"Variable {target} is not isInitialized")
            elif target in self.symbols and type(self.symbols[target]) == Variable:
                if self.symbols[target].isInitialized:
                    self.load_variable(target, out_reg)
                else:

                    if not isStrict and self.loop_depth > 0:
                        self.load_variable(target, out_reg)
                        print(f"Warning: Variable {target} can be uninitialized")
                    else:
                        raise Exception(f"Variable {target} is uninitialized")
            else:
                raise Exception(f"Assigning to array {target} with no index provided")

    def default_load_address(self, target, out_reg=address_reg, isInitialising=False):
        if type(target) == tuple:
            if target[0] == "undeclared":
                raise Exception(f"Assigning to undeclared variable {target[1]}")
            elif target[0] == "array":
                self.load_array_address_at(target[1], target[2], out_reg)
            elif target[0] == "link_t":
                self.load_link_T_address_at(target[1], target[2], out_reg)
            else:
                raise Exception(f"default_load_address")
        else:
            if target in self.links:
                if type(self.links[target]) == Link:
                    self.load_link_address(target, out_reg)
                    self.links[target].isUsed = True
                    if isInitialising:
                        self.links[target].isInitialized = True
                elif type(self.links[target]) == Link_T:
                    self.load_link_T_address_at(target, 0, out_reg)
            elif target in self.symbols:
                if type(self.symbols[target]) == Variable :
                    self.load_variable_address(target, out_reg)
                    if isInitialising:
                        self.symbols[target].isInitialized = True
                elif type(self.symbols[target]) == Array:
                    self.load_array_address_at(target, 0, out_reg)
            else:
                raise Exception(f"Assigning to array {target} with no index provided")

    # Put arr_name value into r_x
    def load_array_at(self, array_name, index, reg=value_reg):
        self.load_array_address_at(array_name, index, reg)
        self.code.append(f"LOAD {reg}")
        if reg != 'a':
            self.code.append(f"PUT {reg}")

    # Generate in r_x address of arr_name
    def load_array_address_at(self, array_name, index, reg=address_reg, reg_h='h'):
        if type(index) == int:
            address = self.procedure.get_address((array_name, index))
            self.gen_const(address, reg)
            return
        elif type(index) != tuple:
            raise Exception(f"Load_array_address_at_error")
        
        if index[1] in self.symbols and type(self.symbols[index[1]]) == Variable:
            if not self.symbols[index[1]].isInitialized:
                if not isStrict and self.loop_depth > 0:
                    print(f"Warning: Trying to use {array_name}[{index[1]}] where variable {index[1]} can be uninitialized")
                else:
                    raise Exception(f"Trying to use {array_name}[{index[1]}] where variable {index[1]} is uninitialized")
            self.load_variable(index[1], reg_h)
            var = self.procedure.get_variable(array_name)
            self.gen_const(var.memory_offset, 'a')
            self.code.append(f"ADD {reg_h}")

        elif index[1] in self.links and type(self.links[index[1]]) == Link:
            self.load_link_variable(index[1], reg_h)
            var = self.procedure.get_variable(array_name)
            self.gen_const(var.memory_offset, 'a')
            self.code.append(f"ADD {reg_h}")

        if reg != 'a':
            self.code.append(f"PUT {reg}")

    # Put var_name value into r_x
    def load_variable(self, name, reg=value_reg, declared=True):
        if declared:
            self.load_variable_address(name, reg, declared)
            self.code.append(f"LOAD {reg}")
            if reg != 'a':
                self.code.append(f"PUT {reg}")
        else:
            raise Exception(f"Undeclared variable {name}")

    # Generate in r_x address of var_name
    def load_variable_address(self, name, reg=address_reg, declared=True):
        if declared:
            address = self.procedure.get_address(name)
            self.gen_const(address, reg)
        else:
            raise Exception(f"Undeclared variable {name}")
        
    def load_link_T_at(self, array_name, index, reg=value_reg):
        self.load_link_T_address_at(array_name, index, reg)
        self.code.append(f"LOAD {reg}")
        if reg != 'a':
            self.code.append(f"PUT {reg}")

    def load_link_T_address_at(self, array_name, index, reg=address_reg, reg_h='h'):
        if type(index) == int:
            address, index = self.procedure.get_address((array_name, index))
            self.gen_const(address, r_a)
            self.code.append(f"LOAD {r_a}")
            self.gen_const(index, reg_h)
            self.code.append(f"ADD {reg_h}")
            if reg != r_a:
                self.code.append(f"PUT {reg}")
            return
        elif type(index) != tuple:
            raise Exception(f"Load_array_address_at_error")
        
        if index[1] in self.symbols and type(self.symbols[index[1]]) == Variable:
            if not self.symbols[index[1]].isInitialized:
                if not isStrict and self.loop_depth > 0:
                    print(f"Warning: Trying to use {array_name}[{index[1]}] where variable {index[1]} can be uninitialized")
                else:
                    raise Exception(f"Trying to use {array_name}[{index[1]}] where variable {index[1]} is uninitialized")
            self.load_variable(index[1], reg_h)
            var = self.procedure.get_variable(array_name)
            self.gen_const(var.memory_offset, 'a')
            self.code.append(f"LOAD {r_a}")
            self.code.append(f"ADD {reg_h}")

        elif index[1] in self.links and type(self.links[index[1]]) == Link:
            self.load_link_variable(index[1], reg_h)
            var = self.procedure.get_variable(array_name)
            self.gen_const(var.memory_offset, 'a')
            self.code.append(f"LOAD {r_a}")
            self.code.append(f"ADD {reg_h}")

        if reg != 'a':
            self.code.append(f"PUT {reg}")

    # Put link_name value into r_x
    def load_link_variable(self, name, reg=value_reg, declared=True):
        if declared:
            address = self.procedure.get_address(name)
            self.gen_const(address, reg)
            self.code.append(f"LOAD {reg}")
            self.code.append(f"LOAD a")
            if reg != 'a':
                self.code.append(f"PUT {reg}")
        else:
            raise Exception(f"Undeclared variable {name}")

    # Generate in r_x address of link_name
    def load_link_address(self, name, reg=address_reg, declared=True):
        if declared:
            address = self.procedure.get_address(name)
            self.gen_const(address, reg)
            self.code.append(f"LOAD {reg}")
            if reg != 'a':
                self.code.append(f"PUT {reg}")
        else:
            raise Exception(f"Undeclared variable {name}")
        
#endregion