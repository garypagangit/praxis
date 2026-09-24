"""Use LibreOffice's bundled Python/UNO to update document indexes and export PDF."""
import sys
from pathlib import Path
import time
import json
import uno
from com.sun.star.beans import PropertyValue


def prop(name,value):
    p=PropertyValue();p.Name=name;p.Value=value;return p


def connect():
    context=uno.getComponentContext()
    resolver=context.ServiceManager.createInstanceWithContext('com.sun.star.bridge.UnoUrlResolver',context)
    for i in range(40):
        try:
            remote=resolver.resolve('uno:socket,host=127.0.0.1,port=20824;urp;StarOffice.ComponentContext')
            return remote.ServiceManager.createInstanceWithContext('com.sun.star.frame.Desktop',remote)
        except Exception:
            time.sleep(.25)
    raise RuntimeError('LibreOffice rendering service did not start')


def main():
    if len(sys.argv)>1 and sys.argv[1]=='--terminate':
        desktop=connect();desktop.terminate();return
    source=Path(sys.argv[1]).resolve();pdf=Path(sys.argv[2]).resolve()
    desktop=connect()
    doc=desktop.loadComponentFromURL(uno.systemPathToFileUrl(str(source)),'_blank',0,
        (prop('Hidden',True),prop('ReadOnly',False),prop('UpdateDocMode',3),
         prop('MacroExecutionMode',uno.getConstantByName('com.sun.star.document.MacroExecMode.NEVER_EXECUTE'))))
    if doc is None:raise RuntimeError('Could not load DOCX')
    try:
        styles=doc.StyleFamilies.getByName('ParagraphStyles')
        for name in ('Contents 1','Contents 2','Contents 3','Index','Figure Index 1','Table Index 1'):
            if styles.hasByName(name):
                s=styles.getByName(name)
                s.CharFontName='Times New Roman';s.CharHeight=12
                s.ParaFirstLineIndent=0
                spacing=uno.createUnoStruct('com.sun.star.style.LineSpacing');spacing.Mode=0;spacing.Height=100
                s.ParaLineSpacing=spacing;s.ParaBottomMargin=106
        counts={}
        for marker,title,style in [
            ('@@TOC@@','Table of Contents',None),
            ('@@FIGURES@@','List of Figures','GWU Figure Caption'),
            ('@@TABLES@@','List of Tables','GWU Table Caption')]:
            search=doc.createSearchDescriptor();search.SearchString=marker
            found=doc.findFirst(search)
            if found is None:raise RuntimeError('Missing index placeholder '+marker)
            index=doc.createInstance('com.sun.star.text.ContentIndex')
            index.Title=title
            index.CreateFromOutline=style is None
            index.Level=2 if style is None else 1
            if style is not None:
                index.CreateFromLevelParagraphStyles=True
                uno.invoke(index.LevelParagraphStyles,'replaceByIndex',(0,uno.Any('[]string',(style,))))
            index.CreateFromMarks=False
            if hasattr(index,'ParaStyleHeading'):index.ParaStyleHeading='GWU Index Heading'
            found.String=''
            doc.Text.insertTextContent(found,index,False)
            index.update()
        for repeat in range(3):
            doc.refresh()
            indexes=doc.getDocumentIndexes()
            for i in range(indexes.Count):indexes.getByIndex(i).update()
            doc.getTextFields().refresh()
        indexes=doc.getDocumentIndexes()
        for i in range(indexes.Count):counts[indexes.getByIndex(i).Title]=i+1
        # Store updated field/index content in the editable delivered DOCX.
        doc.store()
        pdf.parent.mkdir(parents=True,exist_ok=True)
        doc.storeToURL(uno.systemPathToFileUrl(str(pdf)),(prop('FilterName','writer_pdf_Export'),prop('Overwrite',True)))
        print(json.dumps({'status':'PASS','indexes':counts,'pages':doc.CurrentController.PageCount,'pdf':str(pdf)}))
    finally:
        doc.close(True)


if __name__=='__main__':main()
