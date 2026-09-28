import sys,json
from pathlib import Path
sys.path.insert(0,'C:/w/apt_benchmark_20260920/experiments/praxis_next/gwu_final_20260924')
from render_uno import connect,prop,uno
docx=Path(sys.argv[1]).resolve();pdf=Path(sys.argv[2]).resolve()
desktop=connect()
doc=desktop.loadComponentFromURL(uno.systemPathToFileUrl(str(docx)),'_blank',0,(prop('Hidden',True),prop('ReadOnly',False),prop('UpdateDocMode',3)))
try:
 for repeat in range(3):
  doc.refresh();doc.getTextFields().refresh()
 doc.storeToURL(uno.systemPathToFileUrl(str(pdf)),(prop('FilterName','writer_pdf_Export'),prop('FilterData',uno.Any('[]com.sun.star.beans.PropertyValue',(prop('UseTaggedPDF',False),))),prop('Overwrite',True)))
 print(json.dumps({'pages':doc.CurrentController.PageCount,'fields_refreshed':True,'docx_not_resaved':True}))
finally:doc.close(True)
