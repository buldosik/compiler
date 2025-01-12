from procedure import Array, Link, Link_T, Variable
from config import isStrict, log_code

address_reg = '8'
value_reg = '7'
p_0 = '0'

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

    def replace_line_with_new_position(self, text_to_replace, position, text, fisrt_index, last_index):
        for i in range(fisrt_index, last_index):
            self.code[i] = self.code[i].replace(text_to_replace, str(position - i) + text)

    def gen_code_from_procedure(self, name, procedure_table):
        log_code(2, name)
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

    ##
    def gen_proc_jump_back(self, memory_offset):
        self.code.append(f"RTRN {memory_offset} # BACK")

    def gen_code_from_commands(self, commands):
        for command in commands:
            log_code(1, command)
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
                case "for":
                    self.command_for(command)
                case "proc_call":
                    self.command_proc_call(command)
                case _:
                    raise Exception("Not declared command")
    
#region Command

    ##
    def command_write(self, command):
        log_code(2, f"Write + {self.get_current_line()}")
        value = command[1]

        if value[0] == "load":
            self.default_load_var(value[1], out_reg='0')

        elif value[0] == "const":
            self.gen_const(value[1], reg='0')

        self.code.append(f"PUT 0 # WRITE")

    ##
    def command_read(self, command):
        log_code(2, f"read + {self.get_current_line()}")
        target = command[1]

        self.default_load_address(target, '1', isInitialising=True)

        self.code.append(f"GET 0")
        self.code.append(f"STOREI 1 # READ")

    ##
    def command_assign(self, command):
        log_code(2, f"assign + {self.get_current_line()}")
        target = command[1]

        expression = command[2]
        log_code(2, expression)
        self.calculate_expression(expression, value_reg)

        self.default_load_address(target, isInitialising=True)
            
        self.code.append(f"LOAD {value_reg}")
        self.code.append(f"STOREI {address_reg} # ASSIGN")

    ##
    def command_if(self, command):
        log_code(2, f"if + {self.get_current_line()}")
        condition = self.simplify_condition(command[1])
        if isinstance(condition, bool):
            if condition:
                self.gen_code_from_commands(command[2])
        else:
            condition_start = self.get_current_line(withOffset=False)
            self.check_condition(condition, "if_finish")

            if_start = self.get_current_line(withOffset=False)
            self.gen_code_from_commands(command[2])
            
            ifelse_end = self.get_current_line(withOffset=False)
            self.replace_line_with_new_position("if_finish", ifelse_end, " # if_finish", condition_start, if_start)

    ##
    def command_ifelse(self, command):
        log_code(2, f"ifelse + {self.get_current_line()}")
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

            condition_else_start = self.get_current_line(withOffset=False)
            self.gen_code_from_commands(command[3])

            ifelse_end = self.get_current_line(withOffset=False)

            self.replace_line_with_new_position("else_start", condition_else_start, " # else_start", condition_start, if_start)
            self.replace_line_with_new_position("endif", ifelse_end, " # endif", condition_else_start-1, condition_else_start)

    ##
    def command_while(self, command):
        log_code(2, f"while + {self.get_current_line()}")
        condition = self.simplify_condition(command[1])
        if isinstance(condition, bool):
            if condition:
                #infinity loop
                loop_start = self.get_current_line()
                self.gen_code_from_commands(command[2])
                self.code.append(f"JUMP {loop_start - self.get_current_line() + 1}")
        else:
            condition_start = self.get_current_line(withOffset=False)
            self.check_condition(command[1], 'while_end')

            loop_start = self.get_current_line(withOffset=False)
            self.loop_depth += 1
            self.gen_code_from_commands(command[2])
            self.loop_depth -= 1

            self.code.append(f"JUMP {condition_start - self.get_current_line(withOffset=False)} # while condition")

            loop_end = self.get_current_line(withOffset=False)
            #print(loop_end, "---")
            self.replace_line_with_new_position("while_end", loop_end, " # while_end", condition_start, loop_start)

    ##
    def command_until(self, command):
        log_code(2, f"until + {self.get_current_line()}")
        loop_start = self.get_current_line()
        self.loop_depth += 1
        self.gen_code_from_commands(command[2])
        self.loop_depth -= 1

        condition_start = self.get_current_line(withOffset=False)
        self.check_condition(command[1], 'loop_start')

        condition_end = self.get_current_line(withOffset=False)
        self.replace_line_with("loop_start", str(loop_start - self.get_current_line() + 1) + " # loop_start", condition_start, condition_end)

    ##
    def command_for(self, command):
        log_code(1, f"for + {self.get_current_line()}")
        iterator_address = self.procedure.get_address(command[2])
        for_type = command[5]

        if type(command[3]) != tuple:
            command = command[:3] + (('load', command[3]),) + command[3:]
        if type(command[4]) != tuple:
            command = command[:4] + (('load', command[4]),) + command[5:]

        self.calculate_expression(command[3], str(iterator_address))
        self.calculate_expression(command[4], str(iterator_address+1))

        # Checking condition
        condition_start = self.get_current_line(withOffset=False)
        if for_type == -1:
            self.code.append(f'LOAD {iterator_address}')
            self.code.append(f'SUB {iterator_address+1}')
        else:
            self.code.append(f'LOAD {iterator_address+1}')
            self.code.append(f'SUB {iterator_address}')
        self.code.append(f'JNEG for_end')

        # Inner part of for
        for_start = self.get_current_line(withOffset=False)
        self.loop_depth += 1
        self.gen_code_from_commands(command[1])
        self.loop_depth -= 1

        # In/Decresing iterator
        self.code.append(f'LOAD {iterator_address}')
        if for_type == -1:
            self.code.append(f'SUB {11}')
        else:
            self.code.append(f'ADD {11}')
        self.code.append(f'STORE {iterator_address}')
        
        # Jump to start of loop
        self.code.append(f"JUMP {condition_start - self.get_current_line(withOffset=False)} # for condition")

        for_end = self.get_current_line(withOffset=False)
        self.replace_line_with_new_position("for_end", for_end, " # jump -> for_end", condition_start, for_start)

    ##
    def command_proc_call(self, command, return_reg='7'):
        log_code(2, f"proc_call + {self.get_current_line()}")
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
            self.gen_const(current_offset, p_0)
            self.code.append(f"STORE {return_reg}")

            if variable[0] == "load":
                self.default_load_address(variable[1], out_reg='0')
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
            else:
                raise Exception("Command_proc_call Error")
            
            self.code.append(f"STOREI {return_reg}")
            
            current_offset += 1
        
        # Store return line
        self.gen_const(proc_offset, reg='0')
        self.code.append(f"STORE {return_reg}")
        self.code.append(f"SET {self.get_current_line()+3}")
        self.code.append(f"STOREI {return_reg} # Store BACK")
        
        # Jump
        self.code.append(f"JUMP {proc.first_line - self.get_current_line()} # Jump function {proc.name}")

#endregion

    def gen_const(self, const, reg = '9'):
        self.code.append(f"SET {const}")
        if reg != '0':
            self.code.append(f"STORE {reg}")
            

#region calculate_expression

    ##            
    def calculate_expression(self, expression, out_reg='1'):
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

    ##
    def calculate_add(self, expression1, expression2, out_reg='1', second_reg='21'):
        if expression1[0] == expression2[0] == "const":
            self.gen_const(expression1[1] + expression2[1], out_reg)

        elif expression1 == expression2:
            self.calculate_expression(expression1, '0')
            self.code.append(f"ADD 0")
            if out_reg != '0':
                self.code.append(f"STORE {out_reg}")

        else:
            self.calculate_expression(expression1, out_reg)
            self.calculate_expression(expression2, second_reg)
            if out_reg != '0':
                self.code.append(f"LOAD {out_reg}")
            self.code.append(f"ADD {second_reg}")
            if out_reg != '0':
                self.code.append(f"STORE {out_reg}")

    ##
    def calclate_sub(self, expression1, expression2, out_reg='1', second_reg='21'):
        if expression1[0] == expression2[0] == "const":
            val = max(0, expression1[1] - expression2[1])
            if val:
                self.gen_const(val, out_reg)
            else:
                self.code.append(f"LOAD 10")
                if out_reg != '0':
                    self.code.append(f"STORE {out_reg}")

        elif expression1 == expression2:
            self.code.append(f"LOAD 10")
            if out_reg != '0':
                self.code.append(f"STORE {out_reg}")

        else:
            self.calculate_expression(expression1, out_reg)
            self.calculate_expression(expression2, second_reg)
            if out_reg != '0':
                self.code.append(f"LOAD {out_reg}")
            self.code.append(f"SUB {second_reg}")
            if out_reg != '0':
                self.code.append(f"STORE {out_reg}")

    ##
    def calculate_mul(self, expression1, expression2, out_reg='1', second_reg='21', third_reg='22', temp_res_reg='25'):
        if expression1[0] == expression2[0] == "const":
            self.gen_const(expression1[1] * expression2[1], out_reg)
            return

        if expression2[0] == "const":
            val = expression2[1]
            if val == 0:
                self.RST(out_reg)
                return
            elif val == 1:
                self.calculate_expression(expression1, out_reg)
                return
            elif val & (val - 1) == 0:
                self.calculate_expression(expression1, out_reg)
                self.code.append(f"LOAD {out_reg}")
                while val > 1:
                    self.code.append(f"ADD 0")
                    val /= 2
                if out_reg != '0':
                    self.code.append(f"STORE {out_reg}")
                return

        if expression1 == expression2:
            self.calculate_expression(expression1, second_reg)
            self.code.append(f"LOAD {second_reg}")
            self.code.append(f"STORE {third_reg}")
        else:
            self.calculate_expression(expression1, second_reg)
            self.calculate_expression(expression2, third_reg)

        first_line = self.get_current_line(withOffset=False)
        self.RST(temp_res_reg) # 1
        self.code.append(f"LOAD {third_reg}")
        self.code.append(f"SUB {second_reg}")
        self.code.append(f"JPOS #check_last_bit2")
        self.code.append(f"JUMP #check_last_bit1")

        # if second >= third it's better to do $2 * $3

        next_iteration1 = self.get_current_line(withOffset=False)
        self.SHL(second_reg) # 7
        self.SHR(third_reg)

        check_last_bit1 = self.get_current_line(withOffset=False)
        self.code.append(f"LOAD {third_reg}") # 13
        self.code.append(f"JZERO #exit_mul")
        self.code.append(f"HALF")
        self.code.append(f"ADD 0")
        self.code.append(f"SUB {third_reg}")
        self.code.append(f"JNEG {2}")
        self.code.append(f"JUMP #next_iteration1")

        increasing_out1 = self.get_current_line(withOffset=False)
        self.code.append(f"LOAD {temp_res_reg}") # 20
        self.code.append(f"ADD {second_reg}")
        self.code.append(f"STORE {temp_res_reg}")
        self.code.append(f"JUMP #next_iteration1")

        # if second <= third it's better to do $3 * $2

        next_iteration2 = self.get_current_line(withOffset=False)
        self.SHR(second_reg) # 24
        self.SHL(third_reg)

        check_last_bit2 = self.get_current_line(withOffset=False)
        self.code.append(f"LOAD {second_reg}") # 30
        self.code.append(f"JZERO #exit_mul")
        self.code.append(f"HALF")
        self.code.append(f"ADD 0")
        self.code.append(f"SUB {second_reg}")
        self.code.append(f"JNEG {2}")
        self.code.append(f"JUMP #next_iteration2")

        increasing_out2 = self.get_current_line(withOffset=False)
        self.code.append(f"LOAD {temp_res_reg}") # 37
        self.code.append(f"ADD {third_reg}")
        self.code.append(f"STORE {temp_res_reg}")
        self.code.append(f"JUMP #next_iteration2") # 40
        exit_mul = self.get_current_line(withOffset=False)

        
        self.replace_line_with_new_position("#increasing_out1", increasing_out1, " # increasing_out1", first_line, exit_mul)
        self.replace_line_with_new_position("#check_last_bit1", check_last_bit1, " # check_last_bit1", first_line, exit_mul)
        self.replace_line_with_new_position("#next_iteration1", next_iteration1, " # next_iteration1", first_line, exit_mul)
        self.replace_line_with_new_position("#increasing_out2", increasing_out2, " # increasing_out2", first_line, exit_mul)
        self.replace_line_with_new_position("#check_last_bit2", check_last_bit2, " # check_last_bit2", first_line, exit_mul)
        self.replace_line_with_new_position("#next_iteration2", next_iteration2, " # next_iteration2", first_line, exit_mul)
        self.replace_line_with_new_position("#exit_mul", exit_mul, " # exit_mul", first_line, exit_mul)

        if out_reg != temp_res_reg:
            self.code.append(f"LOAD {temp_res_reg}")
            self.code.append(f"STORE {out_reg}")

    ##
    def calculate_div(self, expression1, expression2, out_reg='1', second_reg='21', third_reg='22'):
        if expression1[0] == expression2[0] == "const":
            if expression2[1] > 0:
                self.gen_const(expression1[1] // expression2[1], out_reg)
            else:
                self.RST(out_reg)
            return

        elif expression1[0] == "const" and expression1[1] == 0:
            self.RST(out_reg)
            return
        
        elif expression1 == expression2:
            self.calculate_expression(expression1, second_reg)
            self.code.append(f"LOAD {second_reg}")
            self.code.append(f"JZERO {3}")
            self.code.append(f"LOAD 11")
            self.code.append(f"STORE {out_reg}")
            return

        elif expression2[0] == "const":
            val = expression2[1]
            if val == 0:
                self.RST(out_reg)
                return
            elif val == 1:
                self.calculate_expression(expression1, out_reg)
                return
            elif val & (val - 1) == 0:
                self.calculate_expression(expression1, out_reg)
                self.code.append(f"LOAD {out_reg}")
                while val > 1:
                    self.code.append(f"HALF")
                    val /= 2
                if out_reg != '0':
                    self.code.append(f"STORE {out_reg}")
                return

        self.calculate_expression(expression1, second_reg)
        self.calculate_expression(expression2, third_reg)
        self.perform_division(out_reg=out_reg, dividend_reg=second_reg, divisor_reg=third_reg)

    ##
    def calculate_mod(self, expression1, expression2, out_reg='1', second_reg='21', third_reg='22'):
        if expression1[0] == expression2[0] == "const":
            if expression2[1] > 0:
                self.gen_const(expression1[1] % expression2[1], out_reg)
            else:
                self.RST(out_reg)
            return

        elif expression1 == expression2:
            self.RST(out_reg)
            return

        elif expression1[0] == "const" and expression1[1] == 0:
            self.RST(out_reg)
            return

        elif expression2[0] == "const":
            val = expression2[1]
            if val < 2:
                self.RST(out_reg)
                return
            elif val == 2:
                self.calculate_expression(expression1, second_reg)
                self.code.append(f"LOAD {second_reg}")
                self.code.append(f"HALF")
                self.code.append(f"ADD 0")
                self.code.append(f"STORE {third_reg}")
                self.code.append(f"LOAD {second_reg}")
                self.code.append(f"SUB {third_reg}")
                if out_reg != '0':
                    self.code.append(f"STORE {out_reg}")
                return

        self.calculate_expression(expression1, second_reg)
        self.calculate_expression(expression2, third_reg)
        self.perform_division(out_mod_reg=out_reg, dividend_reg=second_reg, divisor_reg=third_reg)

    ##
    def perform_division(self, out_reg='3', out_mod_reg='4',
                         dividend_reg='21', divisor_reg='22',
                         quotient_reg='23', remainder_reg='24'):

        zero_line = self.get_current_line(withOffset=False)
        self.RST(quotient_reg)                            # 1
        self.RST(remainder_reg)

        # Step 1: Handle division by zero
        self.code.append(f"LOAD {divisor_reg}")
        self.code.append(f"JZERO #exit")     # 6->50 Exit

        # Step 2: Initialize registers
        self.code.append(f"LOAD {dividend_reg}")          # 7
        self.code.append(f"STORE {remainder_reg}")
        self.code.append(f"LOAD {divisor_reg}")
        self.code.append(f"STORE {dividend_reg}")

        # Step 3: Division loop
        self.code.append(f"LOAD {remainder_reg}")         # 11
        self.code.append(f"SUB {dividend_reg}")
        self.code.append(f"JPOS #continue")            # 13->15
        self.code.append(f"JUMP #step4")           # 14->27
        step3mid = self.get_current_line(withOffset=False)
        self.code.append(f"LOAD {dividend_reg}")          # 15
        self.code.append(f"SUB {remainder_reg}")
        self.code.append(f"JPOS #continue")            # 17->19
        self.code.append(f"JUMP #step3shl")            # 18->23
        self.SHR(dividend_reg)
        self.code.append(f"JUMP #step4")            # 22->27
        step3shl = self.get_current_line(withOffset=False)
        self.SHL(dividend_reg)                            # 23
        self.code.append(f"JUMP #step3mid")          # 26->15

        # Step 4: Check remainder and update quotient
        step4 = self.get_current_line(withOffset=False)
        self.code.append(f"LOAD {dividend_reg}")          # 27
        self.code.append(f"SUB {remainder_reg}")
        self.code.append(f"JPOS #exit")      # 29->50 Exit
        self.code.append(f"LOAD {remainder_reg}")         # 30
        self.code.append(f"SUB {dividend_reg}")
        self.code.append(f"STORE {remainder_reg}")
        self.INC(quotient_reg)

        # Step 5: Adjust registers and continue
        step5 = self.get_current_line(withOffset=False)
        self.code.append(f"LOAD {dividend_reg}")          # 36
        self.code.append(f"SUB {remainder_reg}")
        self.code.append(f"JPOS #continue")            # 38->40
        self.code.append(f"JUMP #step4")          # 39->27        
        self.SHR(dividend_reg)

        # Step 6: Check if shifting needed
        self.code.append(f"LOAD {divisor_reg}")           # 43
        self.code.append(f"SUB {dividend_reg}")
        self.code.append(f"JPOS #exit")        # 45->50 Exit
        self.SHL(quotient_reg)                            # 46
        self.code.append(f"JUMP #step5")          # 49->36
        exit_line = self.get_current_line(withOffset=False)

        self.replace_line_with("#continue", "2 # continue", zero_line, exit_line)
        self.replace_line_with_new_position("#step3shl", step3shl, " # step3shl", zero_line, exit_line)
        self.replace_line_with_new_position("#step3mid", step3mid, " # step3mid", zero_line, exit_line)
        self.replace_line_with_new_position("#step4", step4, " # step4", zero_line, exit_line)
        self.replace_line_with_new_position("#step5", step5, " # step5", zero_line, exit_line)
        self.replace_line_with_new_position("#exit", exit_line, " # exit", zero_line, exit_line)


        if out_reg != quotient_reg:
            self.code.append(f"LOAD {quotient_reg}")
            self.code.append(f"STORE {out_reg}")

        if out_mod_reg != remainder_reg:
            self.code.append(f"LOAD {remainder_reg}")
            self.code.append(f"STORE {out_mod_reg}")

#endregion

#region condition

    ##
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

        elif condition[1] == condition[2]:
            if condition[0] in ["ge", "le", "eq"]:
                return True
            else:
                return False

        else:
            return condition

    ##
    def check_condition(self, condition, exit_line='finish',out_reg='1', second_reg='2', third_reg='3'):
        if condition[1][0] == "const" and condition[1][1] == 0:
            if condition[0] == "eq":
                self.calculate_expression(condition[2], p_0)
                self.code.append(f"JZERO {2}")
                self.code.append(f"JUMP {exit_line}")

            elif condition[0] == "ge":
                self.calculate_expression(condition[2], p_0)
                self.code.append(f"JPOS {exit_line}")

            elif condition[0] == "ne":
                self.calculate_expression(condition[2], p_0)
                self.code.append(f"JZERO {exit_line}")

            elif condition[0] == "lt":
                self.calculate_expression(condition[2], p_0)
                self.code.append(f"JPOS {2}")
                self.code.append(f"JUMP {exit_line}")

        elif condition[2][0] == "const" and condition[2][1] == 0:
            if condition[0] == "eq":
                self.calculate_expression(condition[1], p_0)
                self.code.append(f"JZERO {2}")
                self.code.append(f"JUMP {exit_line}")

            elif condition[0] == "le":
                self.calculate_expression(condition[1], p_0)
                self.code.append(f"JPOS {exit_line}")

            elif condition[0] == "ne":
                self.calculate_expression(condition[1], p_0)
                self.code.append(f"JZERO {exit_line}")

            elif condition[0] == "gt":
                self.calculate_expression(condition[1], p_0)
                self.code.append(f"JPOS {2}")
                self.code.append(f"JUMP {exit_line}")

        else:
            self.calculate_expression(condition[1], second_reg)
            self.calculate_expression(condition[2], third_reg)

            if condition[0] == "le":
                self.code.append(f"LOAD {second_reg}")
                self.code.append(f"SUB {third_reg}")
                self.code.append(f"JPOS {exit_line}")

            elif condition[0] == "ge":
                self.code.append(f"LOAD {third_reg}")
                self.code.append(f"SUB {second_reg}")
                self.code.append(f"JPOS {exit_line}")

            elif condition[0] == "lt":
                self.code.append(f"LOAD {third_reg}")
                self.code.append(f"SUB {second_reg}")
                self.code.append(f"JPOS {2}")
                self.code.append(f"JUMP {exit_line}")

            elif condition[0] == "gt":
                self.code.append(f"LOAD {second_reg}")
                self.code.append(f"SUB {third_reg}")
                self.code.append(f"JPOS {2}")
                self.code.append(f"JUMP {exit_line}")

            elif condition[0] == "eq":
                self.code.append(f"LOAD {second_reg}")
                self.code.append(f"SUB {third_reg}")
                self.code.append(f"JZERO {2}")
                self.code.append(f"JUMP {exit_line}")

                self.code.append(f"LOAD {third_reg}")
                self.code.append(f"SUB {second_reg}")
                self.code.append(f"JZERO {2}")
                self.code.append(f"JUMP {exit_line}")

            elif condition[0] == "ne":
                self.code.append(f"LOAD {second_reg}")
                self.code.append(f"SUB {third_reg}")
                self.code.append(f"JZERO {2}")
                self.code.append(f"JUMP {4}")

                self.code.append(f"LOAD {third_reg}")
                self.code.append(f"SUB {second_reg}")
                self.code.append(f"JZERO {exit_line}")

#endregion

#region Load

    ##
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

    ##
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

    ## Put arr_name value into p_x
    def load_array_at(self, array_name, index, reg=value_reg):
        self.load_array_address_at(array_name, index, reg)
        self.code.append(f"LOADI {reg}")
        if reg != '0':
            self.code.append(f"STORE {reg}")

    ## Generate in p_x address of arr_name+index
    def load_array_address_at(self, array_name, index, reg=address_reg):
        if type(index) == int:
            address = self.procedure.get_address((array_name, index))
            self.code.append(f"SET {address}")
            if reg != '0':
                self.code.append(f"STORE {reg}")
            return
        elif type(index) != tuple:
            raise Exception(f"Load_array_address_at_error")
        
        if index[1] in self.symbols and type(self.symbols[index[1]]) == Variable:
            if not self.symbols[index[1]].isInitialized:
                if not isStrict and self.loop_depth > 0:
                    print(f"Warning: Trying to use {array_name}[{index[1]}] where variable {index[1]} can be uninitialized")
                else:
                    raise Exception(f"Trying to use {array_name}[{index[1]}] where variable {index[1]} is uninitialized")
            self.load_variable(index[1], '9')

        elif index[1] in self.links and type(self.links[index[1]]) == Link:
            self.load_link_variable(index[1], '9')

        var = self.procedure.get_variable(array_name)
        self.gen_const(var.memory_offset, '0')
        self.code.append(f"ADD 9")

        if reg != '0':
            self.code.append(f"STORE {reg}")

    ## Put var_name value into p_x
    def load_variable(self, name, reg=value_reg, declared=True):
        if declared:
            self.code.append(f"LOAD {self.procedure.get_address(name)}")
            if reg != '0':
                self.code.append(f"STORE {reg}")
        else:
            raise Exception(f"Undeclared variable {name}")

    ## Generate in r_x address of var_name
    def load_variable_address(self, name, reg=address_reg, declared=True):
        if declared:
            address = self.procedure.get_address(name)
            self.gen_const(address, reg)
        else:
            raise Exception(f"Undeclared variable {name}")

    ## Load array link    
    def load_link_T_at(self, array_name, index, reg=value_reg):
        self.load_link_T_address_at(array_name, index, reg)
        self.code.append(f"LOADI {reg}")
        if reg != '0':
            self.code.append(f"STORE {reg}")

    ## Load address
    def load_link_T_address_at(self, array_name, index, reg=address_reg, reg_h='9'):
        if type(index) == int:
            address, index = self.procedure.get_address((array_name, index))
            self.gen_const(address, reg_h)
            self.code.append(f"STORE {reg_h}")
            self.gen_const(index, p_0)
            self.code.append(f"ADD {reg_h}")
            if reg != p_0:
                self.code.append(f"STORE {reg}")
            return
        elif type(index) != tuple:
            raise Exception(f"Load_array_address_at_error")
        
        if index[1] in self.symbols and type(self.symbols[index[1]]) == Variable:
            print(index[1])
            if not self.symbols[index[1]].isInitialized:
                if not isStrict and self.loop_depth > 0:
                    print(f"Warning: Trying to use {array_name}[{index[1]}] where variable {index[1]} can be uninitialized")
                else:
                    raise Exception(f"Trying to use {array_name}[{index[1]}] where variable {index[1]} is uninitialized")
            self.load_variable(index[1], reg_h)
            var = self.procedure.get_variable(array_name)
            self.code.append(f"LOAD {var.memory_offset}")
            self.code.append(f"ADD {reg_h}")

        elif index[1] in self.links and type(self.links[index[1]]) == Link:
            self.load_link_variable(index[1], reg_h)
            var = self.procedure.get_variable(array_name)
            self.gen_const(var.memory_offset, '0')
            self.code.append(f"LOAD {p_0}")
            self.code.append(f"ADD {reg_h}")

        if reg != '0':
            self.code.append(f"STORE {reg}")

    ## Put link_name value into p_x
    def load_link_variable(self, name, reg=value_reg, declared=True):
        if declared:
            address = self.procedure.get_address(name)
            self.code.append(f"LOADI {address}")
            if reg != '0':
                self.code.append(f"STORE {reg}")
        else:
            raise Exception(f"Undeclared variable {name}")

    ## Generate in r_x address of link_name
    def load_link_address(self, name, reg=address_reg, declared=True):
        if declared:
            address = self.procedure.get_address(name)
            self.code.append(f"LOAD {address}")
            if reg != '0':
                self.code.append(f"STORE {reg}")
        else:
            raise Exception(f"Undeclared variable {name}")
        
#endregion

    def SHR(self, target):
        self.code.append(f"LOAD {target}")
        self.code.append(f"HALF")
        self.code.append(f"STORE {target}") 

    def SHL(self, target):
        self.code.append(f"LOAD {target}")
        self.code.append(f"ADD {target}")
        self.code.append(f"STORE {target}") 

    def RST(self, target):
        self.code.append(f"LOAD 10 # RST")
        self.code.append(f"STORE {target}") 

    def INC(self, target):
        self.code.append(f"LOAD {target}")
        self.code.append(f"ADD 11")
        self.code.append(f"STORE {target}") 
