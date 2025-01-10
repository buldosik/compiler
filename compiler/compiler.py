from sly import Lexer, Parser
from procedure_table import ProcedureTable
from procedure import Link, Link_T, Procedure, Array, Variable
import sys
from config import debug


class ImpLexer(Lexer):
    tokens = {PROGRAM, PROCEDURE, IS, IN, END, WHILE, DO, ENDWHILE, 
              REPEAT, UNTIL, IF, THEN, ELSE, ENDIF, T, READ, WRITE,
              GETS, NEQ, GEQ, LEQ, EQ, GT, LT, PID, NUM, GETS}
    literals = {'+', '-', '*', '/', '%', ',', ':', ';', '(', ')', '[', ']'}
    ignore = ' \t'

    @_(r'\#.*')
    def ignore_comment(self, t):
        self.lineno += t.value.count('\n')

    @_(r'\n+')
    def ignore_newline(self, t):
        self.lineno += len(t.value)

    PROGRAM = r"PROGRAM"

    ENDWHILE = r"ENDWHILE"
    WHILE = r"WHILE"
    DO = r"DO"

    REPEAT = r"REPEAT"
    UNTIL = r"UNTIL"

    ENDIF = r"ENDIF"
    IF = r"IF"
    THEN = r"THEN"
    ELSE = r"ELSE"

    PROCEDURE = r"PROCEDURE"
    IS = r"IS"
    IN = r"IN"
    END = r"END"

    READ = r"READ"
    WRITE = r"WRITE"

    GETS = r":="
    NEQ = r"!="
    GEQ = r">="
    LEQ = r"<="
    EQ = r"="
    GT = r">"
    LT = r"<"
    PID = r"[_a-z]+"

    T = r"T"

    @_(r'\d+')
    def NUM(self, t):
        t.value = int(t.value)
        return t

    def error(self, t):
        raise Exception(f"Illegal character '{t.value[0]}'")


class ImpParser(Parser):
    tokens = ImpLexer.tokens
    currentProcedure = Procedure(0)
    code = None
    procedureTable = ProcedureTable()

#region Program_all
    @_('procedures main')
    def program_all(self, p):
        #print('program_all')
        return self.procedureTable

#endregion

#region Procedures
    
    @_('procedures PROCEDURE proc_head IS declarations IN commands END')
    def procedures(self, p):
        #print(f'procedure {self.currentProcedure.name}')
        self.currentProcedure.set_commands(p.commands)
        self.procedureTable.add_procedure(self.currentProcedure)

    @_('procedures PROCEDURE proc_head IS IN commands END')
    def procedures(self, p):
        #print(f'procedure {self.currentProcedure.name}')
        self.currentProcedure.set_commands(p.commands)
        self.procedureTable.add_procedure(self.currentProcedure)
    
    @_('')
    def procedures(self, p):
        #print('empty')
        pass

#endregion
 
#region Main
        
    @_('program IS declarations IN commands END')
    def main(self, p):
        #print('main')
        self.currentProcedure.set_commands(p.commands)
        self.procedureTable.add_procedure(self.currentProcedure)
    
    @_('program IS IN commands END')
    def main(self, p):
        #print('main')
        self.currentProcedure.set_commands(p.commands)
        self.procedureTable.add_procedure(self.currentProcedure)
    
    @_('PROGRAM')
    def program(self, p):
        self.currentProcedure = Procedure(self.procedureTable.memory_offset)
        self.currentProcedure.name = "PROGRAM"

#endregion
        
#region Commands
        
    @_('commands command')
    def commands(self, p):
        #print('command')
        return p[0] + [p[1]]

    @_('command')
    def commands(self, p):
        #print('command')
        return [p[0]]

#endregion

#region Command

    @_('identifier GETS expression ";"')
    def command(self, p):
        #print('1')
        return "assign", p[0], p[2]

    @_('IF condition THEN commands ELSE commands ENDIF')
    def command(self, p):
        #print('2')
        resp = "ifelse", p[1], p[3], p[5]
        return resp

    @_('IF condition THEN commands ENDIF')
    def command(self, p):
        #print('3')
        resp = "if", p[1], p[3]
        return resp

    @_('WHILE condition DO commands ENDWHILE')
    def command(self, p):
        #print('4')
        resp = "while", p[1], p[3]
        return resp

    @_('REPEAT commands UNTIL condition ";"')
    def command(self, p):
        #print('5')
        return "until", p[3], p[1]

    @_('proc_call ";"')
    def command(self, p):
        #print(f'proc {p[0]}')
        return 'proc_call', p[0]

    @_('READ identifier ";"')
    def command(self, p):
        #print('6')
        return "read", p[1]

    @_('WRITE value ";"')
    def command(self, p):
        #print('7')
        return "write", p[1]

#endregion

#region Proc_head

    @_('PID "(" args_decl ")"')
    def proc_head(self, p):
        self.currentProcedure.name = p[0]


#endregion

#region Proc_call

    @_('PID "(" args ")"')
    def proc_call(self, p):
        if p[0] in self.procedureTable:
            return p[0], p[2]
        elif p[0] == self.currentProcedure.name:
            raise Exception(f"Impossible to call function {p[0]} inside itself, line {p.lineno}")
        else:
            raise Exception(f"Undeclaired function {p[0]}, line {p.lineno}")

#endregion
        
#region Declarations

    @_('declarations "," PID')
    def declarations(self, p):
        #print('declarations')
        self.currentProcedure.add_variable(p[-1])

    @_('declarations "," PID "[" NUM "]"')
    def declarations(self, p):
        #print('declarations_arr')
        self.currentProcedure.add_array(p[2], p[4])

    @_('PID')
    def declarations(self, p):
        #print('declaration')
        self.currentProcedure.add_variable(p[-1])

    @_('PID "[" NUM "]"')
    def declarations(self, p):
        #print('declaration_arr')
        self.currentProcedure.add_array(p[0], p[2])

#endregion
  
#region Args_decl
        
    @_('args_decl "," PID')
    def args_decl(self, p):
        #print('add_link')
        self.currentProcedure.add_link(p[2])

    @_('args_decl "," T PID ')
    def args_decl(self, p):
        #print('add_link_T')
        self.currentProcedure.add_link_T(p[3])

    @_('PID')
    def args_decl(self, p):
        #print('init Proc')
        self.currentProcedure = Procedure(self.procedureTable.memory_offset)
        self.currentProcedure.add_link(p[0])

    @_('T PID')
    def args_decl(self, p):
        #print('init Proc')
        self.currentProcedure = Procedure(self.procedureTable.memory_offset)
        self.currentProcedure.add_link_T(p[1])

#endregion

#region Args
        
    @_('args "," PID')
    def args(self, p):
        if p[2] in self.currentProcedure.symbols:
            return p[0] + [("load", p[2])]
        elif p[2] in self.currentProcedure.links:
            return p[0] + [("load", p[2])]
        else:
            raise Exception(f"Undeclared variable {p[2]}, line {p.lineno}")

    @_('PID')
    def args(self, p):
        if p[0] in self.currentProcedure.symbols:
            return [("load", p[0])]
        elif p[0] in self.currentProcedure.links:
            return [("load", p[0])]
        else:
            raise Exception(f"Undeclared variable {p[0]}, line {p.lineno}")

#endregion
        
#region Expression

    @_('value')
    def expression(self, p):
        return p[0]

    @_('value "+" value')
    def expression(self, p):
        return "add", p[0], p[2]

    @_('value "-" value')
    def expression(self, p):
        return "sub", p[0], p[2]

    @_('value "*" value')
    def expression(self, p):
        return "mul", p[0], p[2]

    @_('value "/" value')
    def expression(self, p):
        return "div", p[0], p[2]

    @_('value "%" value')
    def expression(self, p):
        return "mod", p[0], p[2]

#endregion
        
#region Condition

    @_('value EQ value')
    def condition(self, p):
        return "eq", p[0], p[2]

    @_('value NEQ value')
    def condition(self, p):
        return "ne", p[0], p[2]

    @_('value LT value')
    def condition(self, p):
        return "lt", p[0], p[2]

    @_('value GT value')
    def condition(self, p):
        return "gt", p[0], p[2]

    @_('value LEQ value')
    def condition(self, p):
        return "le", p[0], p[2]

    @_('value GEQ value')
    def condition(self, p):
        return "ge", p[0], p[2]

#endregion
        
#region Value

    @_('NUM')
    def value(self, p):
        return "const", p[0]

    @_('identifier')
    def value(self, p):
        return "load", p[0]

#endregion
        
#region Identifier

    @_('PID')
    def identifier(self, p):
        if p[0] in self.currentProcedure.symbols:
            if type(self.currentProcedure.symbols[p[0]]) == Variable:
                return p[0]
            else:
                raise Exception(f"Assigning to array {p[0]} with no index provided, line {p.lineno}")
        elif p[0] in self.currentProcedure.links:
            if type(self.currentProcedure.links[p[0]]) == Link:
                return p[0]
            else:
                raise Exception(f"Assigning to array {p[0]} with no index provided, line {p.lineno}")
        else:
            raise Exception(f"Undeclared variable {p[0]}, line {p.lineno}")

    @_('PID "[" NUM "]"')
    def identifier(self, p):
        if p[0] in self.currentProcedure.symbols and type(self.currentProcedure.symbols[p[0]]) == Array:
            return "array", p[0], p[2]
        elif p[0] in self.currentProcedure.links and type(self.currentProcedure.links[p[0]]) == Link_T:
            return "link_t", p[0], p[2]
        else:
            raise Exception(f"Undeclared array {p[0]}, line {p.lineno}")
        
    @_('PID "[" PID "]"')
    def identifier(self, p):
        if p[0] in self.currentProcedure.symbols and type(self.currentProcedure.symbols[p[0]]) == Array:
            if p[2] in self.currentProcedure.symbols and type(self.currentProcedure.symbols[p[2]]) == Variable:
                return "array", p[0], ("load", p[2])
            elif p[2] in self.currentProcedure.links and type(self.currentProcedure.links[p[2]]) == Link:
                return "array", p[0], ("load", p[2])
            else:
                raise Exception(f"Undeclared variable {p[2]}, line {p.lineno}")
        elif p[0] in self.currentProcedure.links and type(self.currentProcedure.links[p[0]]) == Link_T:
            if p[2] in self.currentProcedure.symbols and type(self.currentProcedure.symbols[p[2]]) == Variable:
                return "link_t", p[0], ("load", p[2])
            elif p[2] in self.currentProcedure.links and type(self.currentProcedure.links[p[2]]) == Link:
                return "link_t", p[0], ("load", p[2])
            else:
                raise Exception(f"Undeclared variable {p[2]}, line {p.lineno}")
        else:
            raise Exception(f"Undeclared array {p[0]}, line {p.lineno}")

#endregion
        
#region Error

    def error(self, token):
         raise Exception(f"Syntax error: '{token.value}' in line {token.lineno}")

#endregion
        

sys.tracebacklimit = 0
lex = ImpLexer()
pars = ImpParser()
with open(sys.argv[1]) as in_f:
    text = in_f.read()

tokenized = lex.tokenize(text)
pars.parse(tokenized)
procedureTable = pars.procedureTable

if debug:
    for i in procedureTable:
        proc = procedureTable[i]
        print(proc.name, proc.commands)

    print("GEN_CODE")

procedureTable.gen_first_jump()
procedureTable.gen_code()
procedureTable.update_first_jump()
with open(sys.argv[2], 'w') as out_f:
    print(procedureTable.first_line, file=out_f)
    for procedureCode in procedureTable.code:
        for line in procedureCode:
            print(line, file=out_f)
