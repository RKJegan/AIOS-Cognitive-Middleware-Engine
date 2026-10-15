import ast
import operator
import re
from core.narrator import narrate

PLUGIN_NAME = "calculator"
ACTIONS = {"calculate", "calc"}

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow}
_WORDS = [(r"\bdivided by\b|\bover\b", "/"), (r"\btimes\b|\bmultiplied by\b", "*"), (r"\bplus\b", "+"),
          (r"\bminus\b", "-"), (r"\bto the power of\b", "**"), (r"\bmod\b", "%"), (r"(?<=\d)\s*x\s*(?=\d)", "*")]


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = _eval(node.operand)
        return -value if isinstance(node.op, ast.USub) else value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and (abs(right) > 100 or abs(left) > 1e6):
            raise ValueError("that power is too large")
        return _OPS[type(node.op)](left, right)
    raise ValueError("unsupported expression")


def calculate(text):
    expr = text.lower()
    for pattern, symbol in _WORDS:
        expr = re.sub(pattern, symbol, expr)
    expr = re.sub(r"[^0-9+\-*/%.() ]", "", expr).strip()
    if not expr:
        raise ValueError("no calculation found")
    return _eval(ast.parse(expr, mode="eval").body)


def handle(intent):
    try:
        result = calculate(intent.get("name") or "")
    except ZeroDivisionError:
        narrate("You can't divide by zero")
        return {"status": "error", "message": "Division by zero", "data": None}
    except (ValueError, SyntaxError) as e:
        return {"status": "error", "message": f"Couldn't calculate: {e}", "data": None}
    if isinstance(result, float) and result.is_integer():
        result = int(result)
    narrate(f"The answer is {result}")
    return {"status": "success", "message": str(result), "data": result}
