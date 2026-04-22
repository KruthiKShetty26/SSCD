class Symbol:
    def __init__(self, name, type_, scope, line, kind, value=None):
        self.name  = name
        self.type  = type_
        self.scope = scope
        self.line  = line
        self.kind  = kind    # 'variable' | 'function' | 'parameter'
        self.value = value
        self.mem   = self._get_mem(type_)

    def _get_mem(self, t):
        sizes = {'int': 4, 'float': 4, 'double': 8, 'char': 1, 'bool': 1, 'string': 8, 'void': 0}
        return sizes.get(t, 4)

    def to_dict(self):
        return {
            'name':  self.name,
            'type':  self.type,
            'scope': self.scope,
            'line':  self.line,
            'kind':  self.kind,
            'value': self.value,
            'mem':   self.mem,
        }


class SymbolTable:
    def __init__(self):
        self.symbols = []

    def insert(self, symbol):
        # Check for redeclaration in same scope
        for s in self.symbols:
            if s.name == symbol.name and s.scope == symbol.scope:
                return False, f"Redeclaration of '{symbol.name}' in scope '{symbol.scope}'"
        self.symbols.append(symbol)
        return True, "OK"

    def lookup(self, name):
        return [s for s in self.symbols if s.name == name]

    def get_all(self):
        return [s.to_dict() for s in self.symbols]