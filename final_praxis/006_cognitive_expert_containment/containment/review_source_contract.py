"""Read-only AST contract audit; never imports or executes upstream model code."""
import argparse,ast,hashlib,json
from pathlib import Path
def inspect(path):
    raw=path.read_bytes();tree=ast.parse(raw.decode("utf-8-sig"))
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="MiCRoLlamaDecoderLayer")
    forward=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=="forward")
    branch=next(n for n in forward.body if isinstance(n,ast.If) and
                isinstance(n.test,ast.Attribute) and n.test.attr=="use_router")
    def assigns(nodes,name):
        return [n for root in nodes for n in ast.walk(root) if isinstance(n,ast.Assign) and
                any(isinstance(t,ast.Name) and t.id==name for t in n.targets)]
    active=assigns(branch.body,"router_logits");inactive=assigns(branch.orelse,"router_logits")
    assert len(active)==1 and isinstance(active[0].value,ast.Call)
    assert isinstance(active[0].value.func,ast.Attribute) and active[0].value.func.attr=="gate"
    assert any(isinstance(n.value,ast.Name) and n.value.id=="routing_weights" for n in inactive)
    returns=[n for n in forward.body if isinstance(n,ast.Return)]
    assert len(returns)==1 and isinstance(returns[0].value,ast.Tuple)
    assert isinstance(returns[0].value.elts[1],ast.Name) and returns[0].value.elts[1].id=="router_logits"
    return {"source":str(path),"sha256":hashlib.sha256(raw).hexdigest(),
            "active_use_router_true_returns":"raw router logits",
            "inactive_use_router_false_returns":"provided routing weights",
            "active_router_assignment_line":active[0].lineno,
            "inactive_router_assignment_lines":[n.lineno for n in inactive],
            "return_line":returns[0].lineno,"upstream_code_executed":False}
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--source",type=Path,required=True);p.add_argument("--out",type=Path)
    a=p.parse_args();result=inspect(a.source);text=json.dumps(result,indent=2)+"\n"
    if a.out:a.out.write_text(text,encoding="utf-8")
    print(text)

