# Compiler of a Simple Imperative Language
Developed as part of a Formal Languages and Translation Techniques course at Wrocław University of Science and Technology (winter 2023/2024).

## Technologies
Created using:
- **Python 3.10.12**  
- **<a href=https://pypi.org/project/sly/>SLY 0.5</a>**

## How to use
In the main directory run
```bash
python3 compilier/compiler.py <input file> <output file>
```

## Files
- `specs.pdf` – project guidelines including the grammar of the compiled langugage and the assembly commands available in the virtual machine (in Polish),
- `compiler.py` – the lexer and the parser,  
- `procedure.py` – store commands, links (args), symbols (local_variables)
- `procedure_table.py` – memory and output code management,
- `code_generator.py` – generation of the output assembly code from the syntax tree.


The `examples*` directories contain some examples that allow to test the output code. Most of them were written by <a href="https://www.cs.pwr.edu.pl/gebala">Maciej Gębala</a> and <a href="https://cs.pwr.edu.pl/slowik/"> Marcin Słowik</a>. They can be conveniently run with

```bash
./run_programs.sh 
```
```bash
./run_examples2023.sh
```

Error handling tests can be run using
```bash
./run_errors.sh
```

Also you can run any test using
```bash
./run_test.sh <input file> <output file=output.txt>
```

```bash
./run_test_cln.sh <input file> <output file=output.txt>
```

All bash scripts require a pre-compiled virtual machine executable in the virtual_machine directory. The machine was developed by the lecturer, Maciej Gębala. Its sources can be found inside the `virtual_machine` directory. In order for all tests to run correctly, build it with the <a href="https://www.ginac.de/CLN/">CLN library</a> installed.
