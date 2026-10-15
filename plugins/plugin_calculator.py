import ast
import operator
from core.narrator import narrate

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg}


def _eval(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp):
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("unsupported expression")


def calculate(intent):
    expr = (intent.get("name") or "").lower()
    expr = expr.replace("times", "*").replace("plus", "+").replace("minus", "-").replace("divided by", "/")
    try:
        result = _eval(ast.parse(expr, mode="eval").body)
        narrate(f"{expr} = {result}")
        return {"status": "success", "message": str(result), "data": {"result": result}}
    except Exception:
        return {"status": "error", "message": "Couldn't evaluate that expression", "data": None}


def tell_time(intent):
    from datetime import datetime
    now = datetime.now().strftime("%H:%M")
    narrate(f"It's {now}")
    return {"status": "success", "message": now, "data": {"time": now}}


PLUGIN_ACTIONS = {"calculate": calculate, "time": tell_time}
