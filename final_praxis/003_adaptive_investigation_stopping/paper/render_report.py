"""Use the shared DOCX formatter with a Pillow GMR renderer on this Windows host.

The matplotlib font callback stalled on the host. This changes diagram layout
only, preserving nodes and edges; shared and frozen source files are unchanged.
"""
import importlib.util
from pathlib import Path
import re
import sys
import textwrap
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[3]

def render_gmr(source,path):
    nodes=dict(re.findall(r"([A-Za-z]\w*)\[([^\]]+)\]",source))
    simple=re.sub(r"([A-Za-z]\w*)\[[^\]]+\]",r"\1",source)
    edges=re.findall(r"([A-Za-z]\w*)\s*-->\s*([A-Za-z]\w*)",simple)
    if not nodes or any(a not in nodes or b not in nodes for a,b in edges):return False
    # The report's frozen GMR is a simple eight-node chain; fail rather than invent branches.
    order=list(nodes)
    if edges!=list(zip(order,order[1:])):raise ValueError("Unexpected GMR topology")
    width=1300;step=145;height=len(order)*step+50
    image=Image.new("RGB",(width,height),"white");draw=ImageDraw.Draw(image)
    font=ImageFont.load_default(size=30)
    for index,name in enumerate(order):
        top=25+index*step;bottom=top+105
        draw.rounded_rectangle((50,top,width-50,bottom),radius=16,fill="#E8EFF2",outline="#47636E",width=3)
        label=nodes[name].strip('"').replace("×","x")
        lines=textwrap.wrap(label,width=62)
        text="\n".join(lines)
        bounds=draw.multiline_textbbox((0,0),text,font=font,spacing=5,align="center")
        textwidth=bounds[2]-bounds[0];textheight=bounds[3]-bounds[1]
        draw.multiline_text(((width-textwidth)/2,top+(105-textheight)/2-bounds[1]),text,font=font,fill="#173A4A",spacing=5,align="center")
        if index<len(order)-1:
            draw.line((width/2,bottom+3,width/2,bottom+28),fill="#47636E",width=4)
            draw.polygon([(width/2-9,bottom+24),(width/2+9,bottom+24),(width/2,bottom+36)],fill="#47636E")
    image.save(path,dpi=(200,200));return True

def main():
    module_path=ROOT/"scripts/build_final_praxis_docx.py"
    spec=importlib.util.spec_from_file_location("praxis_docx_formatter",module_path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.diagram_from_mermaid=render_gmr
    sys.argv=[str(module_path),"--experiment","003","--render"]
    module.main()

if __name__=="__main__":main()
