from lexer import tokenize, TYPE_WORDS
from symbol_table import Symbol, SymbolTable


def parse(source):
    tokens, lex_errors = tokenize(source)
    table  = SymbolTable()
    errors = list(lex_errors)

    scope_stack = ['global']
    depth = 0
    seen  = set()

    i = 0
    while i < len(tokens):
        t = tokens[i]

        # ── ERROR token: misspelled keyword like 'retur' ─────────────────
        if t['type'] == 'ERROR':
            sym_key = f"{t['value']}@error_{t['line']}"
            if sym_key not in seen:
                seen.add(sym_key)
                sym = Symbol(
                    name  = t['value'],
                    type_ = 'unknown',
                    scope = scope_stack[-1],
                    line  = t['line'],
                    kind  = 'unknown',
                    value = 'ERROR'
                )
                table.insert(sym)

        # ── ERROR_OP: incomplete expression like ab+ ──────────────────────
        elif t['type'] == 'ERROR_OP':
            # Find the left-hand identifier (token before the operator)
            prev = tokens[i - 1] if i > 0 else None
            expr_name = (prev['value'] if prev else '?') + t['value']
            sym_key = f"expr_error@line_{t['line']}"
            if sym_key not in seen:
                seen.add(sym_key)
                sym = Symbol(
                    name  = f"{expr_name}?",
                    type_ = 'unknown',
                    scope = scope_stack[-1],
                    line  = t['line'],
                    kind  = 'unknown',
                    value = 'INCOMPLETE EXPR'
                )
                table.insert(sym)

        # ── Entering a block ──────────────────────────────────────────────
        elif t['value'] == '{':
            depth += 1
            prev_id = None
            for j in range(i - 1, max(i - 6, -1), -1):
                if tokens[j]['value'] in (')', '{', '}', ';'):
                    break
                if tokens[j]['type'] == 'ID':
                    prev_id = tokens[j]['value']
                    break
            scope_stack.append(prev_id or f'block_{depth}')

        # ── Leaving a block ───────────────────────────────────────────────
        elif t['value'] == '}':
            if len(scope_stack) > 1:
                scope_stack.pop()
            depth = max(0, depth - 1)

        # ── Type keyword → check for declaration ─────────────────────────
        elif t['type'] == 'KEYWORD' and t['value'] in TYPE_WORDS:
            type_kw = t['value']
            j = i + 1

            while j < len(tokens) and tokens[j]['value'] in ('*', '&'):
                j += 1

            if j < len(tokens) and tokens[j]['type'] == 'ID':
                name  = tokens[j]['value']
                scope = scope_stack[-1]
                kind  = 'variable'
                value = None

                # Function: name followed by (
                if j + 1 < len(tokens) and tokens[j + 1]['value'] == '(':
                    kind = 'function'
                    k = j + 2
                    while k < len(tokens) and tokens[k]['value'] != ')':
                        if tokens[k]['type'] == 'KEYWORD' and tokens[k]['value'] in TYPE_WORDS:
                            pt = tokens[k]['value']
                            m2 = k + 1
                            while m2 < len(tokens) and tokens[m2]['value'] in ('*', '&'):
                                m2 += 1
                            if m2 < len(tokens) and tokens[m2]['type'] == 'ID':
                                pname = tokens[m2]['value']
                                pkey  = f'{pname}@{name}'
                                if pkey not in seen:
                                    seen.add(pkey)
                                    sym = Symbol(pname, pt, name, tokens[k]['line'], 'parameter')
                                    ok, msg = table.insert(sym)
                                    if not ok:
                                        errors.append({'line': tokens[k]['line'], 'message': msg})
                        k += 1

                # Variable with = assignment
                elif j + 1 < len(tokens) and tokens[j + 1]['value'] == '=':
                    if j + 2 < len(tokens):
                        val_tok = tokens[j + 2]

                        # Check: right side is ERROR_OP (ab+) or ends abruptly
                        if j + 3 < len(tokens) and tokens[j + 3]['type'] == 'ERROR_OP':
                            # e.g. int result = ab+
                            errors.append({
                                'line': t['line'],
                                'message': f"Incomplete expression for '{name}' at line {t['line']}: '{val_tok['value']}{tokens[j+3]['value']}' — missing right operand"
                            })
                            kind  = 'unknown'
                            value = f"{val_tok['value']}{tokens[j+3]['value']}? (incomplete)"

                        elif j + 3 < len(tokens) and tokens[j + 3]['value'] in ('+', '-', '*', '/'):
                            # Normal operator — check if right operand missing
                            after_op = tokens[j + 4] if j + 4 < len(tokens) else None
                            if after_op and after_op['value'] in (';', '}', ')') :
                                errors.append({
                                    'line': t['line'],
                                    'message': f"Incomplete expression for '{name}' at line {t['line']}: missing right operand after '{tokens[j+3]['value']}'"
                                })
                                kind  = 'unknown'
                                value = f"{val_tok['value']}{tokens[j+3]['value']}? (incomplete)"
                            else:
                                value = val_tok['value']
                        else:
                            value = val_tok['value']

                # Insert symbol
                sym_key = f'{name}@{scope}'
                if sym_key not in seen:
                    seen.add(sym_key)
                    sym = Symbol(name, type_kw, scope, t['line'], kind, value)
                    ok, msg = table.insert(sym)
                    if not ok:
                        errors.append({'line': t['line'], 'message': msg})

        i += 1

    # Flatten errors to strings, remove duplicates
    seen_msgs = set()
    error_strings = []
    for e in errors:
        msg = f"Line {e['line']}: {e['message']}" if isinstance(e, dict) else str(e)
        if msg not in seen_msgs:
            seen_msgs.add(msg)
            error_strings.append(msg)

    return table.get_all(), error_strings, tokens