import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
const require=createRequire('C:/Users/garyp/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/package.json');
const {PresentationFile,FileBlob}=require('@oai/artifact-tool');
const tmp='C:/Users/garyp/AppData/Local/Temp/codex-presentations/praxis-integrated-20260928/tmp';
const out='C:/Users/garyp/OneDrive/Documents/codex/output/praxis_integrated_20260928';
const content=JSON.parse(await fs.readFile(tmp+'/integrated-content.json','utf8'));
const pres=await PresentationFile.importPptx(await FileBlob.load(tmp+'/template-starter.pptx'));
await fs.mkdir(tmp+'/final-render',{recursive:true});
for(let i=0;i<content.length;i++){
 const slide=pres.slides.items[i], c=content[i]; c.notes=c.notes.replace('contains 30 references','contains 33 references');
 const layout=JSON.parse(await fs.readFile(tmp+`/starter-layout/starter-slide-${String(i+1).padStart(2,'0')}.layout.json`,'utf8'));
 const title=slide.shapes.getById(i===0?'2':'3');
 title.text=c.title; title.text.style={typeface:'Arial',fontSize:i===0?42:40,bold:true,color:i===0?'#FFFFFF':'#033c5a'};
 if(i===0){const date=slide.shapes.getById('4');date.text='Integrated review edition\nSeptember 28, 2026';date.text.style={typeface:'Arial',fontSize:25.33,color:'#FFFFFF'};}
 else {
  if(c.body.length){const b=slide.shapes.getById('2');b.text=c.body.map(t=>({runs:[t],bulletCharacter:'•',marginLeft:22,indent:-17,spaceAfter:18}));b.text.style={typeface:'Arial',fontSize:29.33,color:'#727272',verticalAlignment:'top'};}
  const item=layout.elements.find(e=>e.name==='Evidence source');
  if(!item)throw Error('Missing footer '+(i+1));
  const footer=slide.shapes.getById(item.id);footer.text=`${String(i+1).padStart(2,'0')}  |  ${c.citation}`;footer.text.style={typeface:'Arial',fontSize:15,color:'#5a6873'};
 }
 slide.speakerNotes.clear();slide.speakerNotes.textFrame.setText(c.notes+'\n\nEvidence: '+c.citation+'\nAuthoring support: AI-assisted artifact preparation and computational checks; author review is required under applicable GWU policy.');
 const stem=tmp+`/final-render/slide-${String(i+1).padStart(2,'0')}`;
 const png=await pres.export({slide,format:'png',scale:1});await fs.writeFile(stem+'.png',new Uint8Array(await png.arrayBuffer()));
 const lay=await slide.export({format:'layout'});await fs.writeFile(stem+'.json',await lay.text());
}
const pptx=await PresentationFile.exportPptx(pres);await pptx.save(out+'/Gary_Pagan_GWU_Praxis_Defense.pptx');
await fs.writeFile(out+'/Defense_Speaker_Notes.txt',content.map((s,i)=>`SLIDE ${i+1}: ${s.title}\n\n${s.notes}\n\nSOURCE: ${s.citation}`).join('\n\n'+'='.repeat(60)+'\n\n'));
console.log(JSON.stringify({slides:content.length,main:25,backup:12,exported:true}));
