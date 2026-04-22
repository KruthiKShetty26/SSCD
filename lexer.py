import re

KEYWORDS = {
    'int', 'float', 'char', 'double', 'string', 'bool', 'void',
    'return', 'if', 'else', 'while', 'for', 'do', 'switch', 'case',
    'class', 'struct', 'public', 'private', 'protected',
    'true', 'false', 'new', 'delete', 'include', 'define'
}

TYPE_WORDS = {'int', 'float', 'char', 'double', 'string', 'bool', 'void'}

MISSPELLED_KEYWORDS = {
    'retur':    'return',
    'retrun':   'return',
    'retun':    'return',
    'retrn':    'return',
    'flot':     'float',
    'flaot':    'float',
    'sting':    'string',
    'srting':   'string',
    'bol':      'bool',
    'viod':     'void',
    'vod':      'void',
    'mian':     'main',
    'interger': 'int',
    'doubel':   'double',
}

TOKEN_PATTERNS = [
    ('COMMENT_SL', r'//[^\n]*'),
    ('COMMENT_ML', r'/\*[\s\S]*?\*/'),
    ('STRING',     r'"[^"]*"'),
    ('CHAR',       r"'[^'\\]'|'\\.'"),
    ('FLOAT',      r'\d+\.\d*|\.\d+'),
    ('INT',        r'\d+'),
    ('ID',         r'[a-zA-Z_]\w*'),
    ('OP',         r'==|!=|<=|>=|&&|\|\||[+\-*/%=<>!&|^~]'),
    ('PUNCT',      r'[{}()\[\];,.]'),
    ('NEWLINE',    r'\n'),
    ('SKIP',       r'[ \t]+'),
]

MASTER = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in TOKEN_PATTERNS)


def tokenize(source):
    tokens = []
    lex_errors = []
    line = 1

    for m in re.finditer(MASTER, source):
        kind  = m.lastgroup
        value = m.group()

        if kind == 'NEWLINE':
            line += 1
            continue
        if kind in ('SKIP', 'COMMENT_SL', 'COMMENT_ML'):
            line += value.count('\n')
            continue

        if kind == 'ID':
            if value in KEYWORDS:
                kind = 'KEYWORD'
            elif value in MISSPELLED_KEYWORDS:
                suggestion = MISSPELLED_KEYWORDS[value]
                lex_errors.append({
                    'line': line,
                    'message': f"Misspelled keyword '{value}' at line {line} — did you mean '{suggestion}'?"
                })
                kind = 'ERROR'

        tokens.append({'type': kind, 'value': value, 'line': line})

    # ── Post-process: detect incomplete expressions like  ab+  ──────────
    # Pattern: ID or number followed by operator (+,-,*,/) followed by
    # a NEWLINE-equivalent (next token is on a different line OR is ; } )
    for i, tok in enumerate(tokens):
        if tok['type'] == 'OP' and tok['value'] in ('+', '-', '*', '/'):
            next_tok = tokens[i + 1] if i + 1 < len(tokens) else None
            prev_tok = tokens[i - 1] if i > 0 else None

            # Right side is missing: next token is ; } ) or a new statement keyword
            if next_tok and next_tok['value'] in (';', '}', ')'):
                lex_errors.append({
                    'line': tok['line'],
                    'message': f"Incomplete expression at line {tok['line']}: operator '{tok['value']}' has no right operand — e.g. 'ab+' is invalid"
                })
                tok['type'] = 'ERROR_OP'

            # Right side missing: next token is a KEYWORD (new statement started)
            elif next_tok and next_tok['type'] == 'KEYWORD':
                lex_errors.append({
                    'line': tok['line'],
                    'message': f"Incomplete expression at line {tok['line']}: operator '{tok['value']}' has no right operand"
                })
                tok['type'] = 'ERROR_OP'

            # Right side missing: next token is on a DIFFERENT line (implicit newline)
            elif next_tok and next_tok['line'] > tok['line']:
                lex_errors.append({
                    'line': tok['line'],
                    'message': f"Incomplete expression at line {tok['line']}: operator '{tok['value']}' has no right operand — expression ends abruptly"
                })
                tok['type'] = 'ERROR_OP'

    # ── Post-process: detect missing semicolons ──────────────────────────
    # Pattern: a statement ends with ID or number, but next token is NOT ; or }
    # and is on a DIFFERENT line
    for i, tok in enumerate(tokens):
        if tok['type'] in ('ID', 'INT', 'FLOAT') and i + 1 < len(tokens):
            next_tok = tokens[i + 1]
            # If next token is on a new line AND is a KEYWORD or TYPE (new statement)
            if (next_tok['line'] > tok['line']
                    and next_tok['type'] == 'KEYWORD'
                    and next_tok['value'] in TYPE_WORDS | {'return', 'if', 'while', 'for'}):
                # Check that the current line didn't already end with ;
                # by looking back for a semicolon on the same line
                has_semi = any(
                    t['value'] == ';' and t['line'] == tok['line']
                    for t in tokens[max(0, i-5):i+1]
                )
                if not has_semi:
                    lex_errors.append({
                        'line': tok['line'],
                        'message': f"Missing semicolon at line {tok['line']} — statement does not end with ';'"
                    })

    return tokens, lex_errors