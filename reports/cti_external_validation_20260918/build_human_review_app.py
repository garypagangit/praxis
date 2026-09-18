"""Build an offline form from the blinded packet and blank template only."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIELDS = {'review_id', 'reviewer', 'date', 'answer', 'citation', 'applicability', 'ambiguity', 'notes'}


def read_jsonl(path):
    raw = path.read_bytes()
    return raw, [json.loads(line) for line in raw.decode('utf-8').splitlines() if line.strip()]


def build(packet_path, template_path, output):
    packet_raw, packet = read_jsonl(packet_path)
    template_raw, template = read_jsonl(template_path)
    expected_ids = [f'CTI-H{i:03d}' for i in range(1, 51)]
    if len(packet) != 50 or len(template) != 50:
        raise ValueError('Exactly 50 blinded items and blank responses are required')
    if [r.get('review_id') for r in packet] != expected_ids or [r.get('review_id') for r in template] != expected_ids:
        raise ValueError('Packet and template IDs/order must match CTI-H001 through CTI-H050')
    for row in packet:
        if set(row) != {'review_id', 'question', 'options', 'evidence'}:
            raise ValueError('Unexpected packet field: only blinded question/options/evidence are permitted')
        if not isinstance(row['question'], str) or not row['question'].strip():
            raise ValueError('A nonempty question is required')
        if not isinstance(row['options'], dict) or set(row['options']) != set('ABCD'):
            raise ValueError('Exactly four displayed options are required')
        if any(not isinstance(v, str) or not v.strip() for v in row['options'].values()):
            raise ValueError('Option text must be nonempty')
        if not isinstance(row['evidence'], list):
            raise ValueError('Evidence must be a list')
        for item in row['evidence']:
            if set(item) != {'kind', 'score', 'text'} or not isinstance(item['text'], str):
                raise ValueError('Unexpected evidence fields')
    for row in template:
        if set(row) != FIELDS or any(row[key] != '' for key in FIELDS-{'review_id'}):
            raise ValueError('Response template must contain only the original blank fields')
    payload = {'packet': packet, 'template': template, 'fields': list(template[0]),
               'packet_sha256': hashlib.sha256(packet_raw).hexdigest(),
               'template_sha256': hashlib.sha256(template_raw).hexdigest()}
    encoded = json.dumps(payload, ensure_ascii=True, separators=(',', ':'), allow_nan=False)
    # Prevent source text from ending the nonexecuting JSON script element.
    encoded = encoded.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    raw = HTML.replace('__REVIEW_DATA__', encoded).encode('utf-8')
    output.write_bytes(raw)
    return {'path': str(output), 'items': 50, 'sha256': hashlib.sha256(raw).hexdigest(),
            'bytes': len(raw), 'packet_sha256': payload['packet_sha256'],
            'template_sha256': payload['template_sha256'],
            'human_reviews_completed_by_builder': 0, 'external_resources': 0}


HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; img-src 'none'; font-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'">
<title>CTI · Independent human review</title>
<style>
:root{color-scheme:light;--ink:#172e37;--muted:#536a72;--line:#d6e2e4;--teal:#12645f;--wash:#e7f3ef;--bg:#f2f6f5;--focus:#a75316}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1060px;margin:0 auto;padding:36px 24px 60px}header{margin-bottom:24px}.eyebrow{color:var(--teal);font-weight:750;font-size:12px;letter-spacing:.12em;text-transform:uppercase}
h1{font-size:clamp(28px,4vw,40px);line-height:1.12;letter-spacing:-.035em;margin:10px 0 12px}h2{font-size:23px;line-height:1.4;margin:0 0 20px}h3{font-size:17px;margin:0 0 12px}p{margin:8px 0}.intro{max-width:790px;color:var(--muted)}.tag{display:inline-block;background:var(--wash);color:var(--teal);border:1px solid #bbd9cd;border-radius:20px;font-size:12px;padding:4px 10px;font-weight:700}
.card{background:white;border:1px solid var(--line);border-radius:16px;padding:24px;margin:16px 0;box-shadow:0 3px 12px #14362e04}.setup{display:grid;grid-template-columns:1fr 1.4fr 1fr;gap:18px}.field label,.legend{display:block;font-weight:700;font-size:14px;margin-bottom:6px}input,select,textarea{width:100%;font:inherit;border:1px solid #a5b9bf;border-radius:8px;color:var(--ink);background:white;padding:10px 12px}textarea{resize:vertical;min-height:78px}input:focus,select:focus,textarea:focus,button:focus-visible,summary:focus-visible{outline:3px solid #e9ac6d;outline-offset:3px}button{font:inherit;cursor:pointer;border:1px solid #aac0c3;background:white;border-radius:9px;color:var(--ink);padding:10px 15px;font-weight:650}button:hover:not(:disabled){background:#edf4f3}button:disabled{opacity:.45;cursor:default}.primary{background:var(--teal);color:white;border-color:var(--teal)}.primary:hover:not(:disabled){background:#0b4d49}.danger{color:#8c3e30;background:#fff9f7;border-color:#d5b4ab;font-size:13px}.hint{color:var(--muted);font-size:13px}.toolbar,.progress-top,.question-meta,.bottom{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap}.progress-top strong{font-size:20px}.progress{height:9px;background:#e7edeb;border-radius:10px;overflow:hidden;margin:12px 0}.progress-fill{height:100%;width:0;background:var(--teal);transition:width .15s}.toolbar{margin-top:18px}.save{font-size:13px;color:var(--muted)}.save.error{color:#8c3e30}.steps{padding-left:20px;color:var(--muted);font-size:14px}.steps li{margin:7px 0}.question-meta{margin-bottom:14px}.question-meta span{font-size:13px;color:var(--muted)}.question-text{white-space:pre-wrap;overflow-wrap:anywhere}.options{display:grid;gap:10px;margin-bottom:22px}.option{display:flex;gap:14px;background:#f5f8f7;border-radius:9px;padding:13px 15px}.letter{font-weight:800;color:var(--teal);flex:0 0 19px}.option-text{white-space:pre-wrap;overflow-wrap:anywhere}details{border:1px solid var(--line);border-radius:10px;padding:13px 16px;margin:18px 0}summary{cursor:pointer;font-weight:700}details[open] summary{margin-bottom:12px}.fact{padding:14px 0;border-top:1px solid var(--line)}.fact:first-child{border-top:none}.fact p{white-space:pre-wrap;overflow-wrap:anywhere;font-size:14px}.fact small{color:var(--muted);font-size:12px;text-transform:capitalize}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.full{grid-column:1/-1}fieldset{border:0;padding:0;margin:0;min-width:0}fieldset:disabled{opacity:.6}.answer-row{display:flex;flex-wrap:wrap;gap:10px}.answer-option{position:relative;cursor:pointer}.answer-option input{position:absolute;opacity:0;width:1px;height:1px}.answer-option span{display:block;padding:10px 20px;border:1px solid #a5b9bf;border-radius:8px;font-size:15px;font-weight:750}.answer-option input:checked+span{background:var(--wash);border:2px solid var(--teal);padding:9px 19px;color:var(--teal)}.answer-option input:focus-visible+span{outline:3px solid #e9ac6d;outline-offset:3px}.bottom{border-top:1px solid var(--line);padding-top:20px;margin-top:24px}.nav-grid{display:grid;grid-template-columns:repeat(10,1fr);gap:8px;margin-top:15px}.nav-grid button{padding:8px 3px;font-size:13px}.nav-grid button.done{background:var(--wash);color:var(--teal);border-color:#8cb8a5}.nav-grid button.current{outline:2px solid var(--teal);outline-offset:2px}.footnote{margin:24px 0;color:var(--muted);font-size:13px}.hash{font:12px/1.6 ui-monospace,monospace;overflow-wrap:anywhere}.notice{background:#fff6e7;border-left:3px solid #b77c2a;padding:12px 15px;font-size:14px;color:#674717;margin:16px 0}#exportMessage{min-height:1.5em;font-size:14px;color:var(--teal)}
@media(max-width:640px){main{padding:24px 14px 40px}.card{padding:18px}.setup,.form-grid{grid-template-columns:1fr}.full{grid-column:1}.nav-grid{grid-template-columns:repeat(5,1fr)}.toolbar button{width:100%}.answer-option span{padding:10px 16px}.answer-option input:checked+span{padding:9px 15px}h2{font-size:20px}}
</style>
</head>
<body><main>
<header><div class="eyebrow">Praxis / CTI evidence quality</div><h1>Independent human review</h1>
<p class="intro">Read 50 security questions and judge the supplied evidence. Your answers stay in this browser until you download them. This file works offline.</p>
<p><span class="tag">Blinded packet · human review pending</span></p></header>
<section class="card" aria-label="Reviewer setup">
<div class="setup">
<div class="field"><label for="reviewerSlot">Your assigned reviewer number</label><select id="reviewerSlot"><option value="">Choose reviewer 1 or 2</option><option value="1">Reviewer 1</option><option value="2">Reviewer 2</option></select></div>
<div class="field"><label for="reviewerName">Your name or reviewer identifier</label><input id="reviewerName" type="text" maxlength="200" autocomplete="off" placeholder="Enter your name" disabled></div>
<div class="field"><label for="reviewDate">Review date</label><input id="reviewDate" type="date" disabled></div>
</div>
<p class="hint">Give each reviewer a separate copy of this file and use a separate browser profile or device. Do not read the other reviewer's responses before finishing your own.</p>
<details><summary>How to complete this review</summary><ol class="steps">
<li>Read the question and all choices, then open the retrieved evidence. Use your own security knowledge and authoritative sources.</li>
<li>Choose A–D or <strong>Uncertain</strong>. Rate whether the evidence applies and whether the question has one clear answer.</li>
<li>Add a supporting URL and section/version. If no defensible answer or source is available, choose Uncertain and explain in Notes. Never invent a citation.</li>
<li>Download your responses regularly and when finished. Send your own file to the review coordinator; nothing is submitted automatically.</li>
</ol><p class="hint">This app does not contain released answers, dataset identities, source-family labels, model outputs, or another reviewer's answers. Fifty questions are a quality audit, not a population accuracy estimate.</p></details>
<div class="progress-top"><strong id="progressText">0 of 50 complete</strong><span id="citationCount" class="hint">0 citations supplied</span></div>
<div class="progress" role="progressbar" aria-label="Review completion" aria-valuemin="0" aria-valuemax="50" aria-valuenow="0" id="progressBar"><div class="progress-fill" id="progressFill"></div></div>
<p class="hint">Complete = reviewer, date, answer, both ratings, and a citation (or an Uncertain answer with an explanatory note). Counts describe this local draft only; independent review and adjudication remain pending.</p>
<div class="toolbar"><span class="save" id="saveStatus" role="status">Choose your reviewer number to begin.</span><button id="exportButton" class="primary" type="button" disabled>Download responses (.jsonl)</button></div>
<div id="exportMessage" role="status" aria-live="polite"></div>
</section>
<section class="card" aria-labelledby="questionHeading">
<div class="question-meta"><span id="position">Question 1 of 50</span><span id="reviewId"></span></div>
<h2 id="questionHeading" class="question-text" tabindex="-1"></h2>
<div class="options" id="optionList"></div>
<details id="evidenceDetails"><summary id="evidenceSummary">Retrieved evidence</summary><div id="evidenceList"></div></details>
<div class="notice" id="startNotice">Choose your assigned reviewer number above to enter responses.</div>
<fieldset id="responseFields" disabled><legend class="legend">Your independent judgment</legend>
<div class="form-grid">
<div class="full"><div class="legend" id="answerLabel">Your answer</div><div class="answer-row" id="answerChoices" role="radiogroup" aria-labelledby="answerLabel"></div></div>
<div class="field"><label for="applicability">How does the retrieved evidence apply?</label><select id="applicability"></select><p class="hint">Shared security terms alone do not establish support. Use Contradictory for a material conflict, not simple irrelevance.</p></div>
<div class="field"><label for="ambiguity">Is the question unambiguous?</label><select id="ambiguity"></select><p class="hint">Name relevant versions or missing conditions in Notes.</p></div>
<div class="field full"><label for="citation">Supporting source and specific section</label><textarea id="citation" maxlength="10000" placeholder="Authoritative URL, then the section, technique, version, or passage"></textarea></div>
<div class="field full"><label for="notes">Notes / explanation of uncertainty</label><textarea id="notes" maxlength="20000" placeholder="Explain ambiguity, missing conditions, conflicting evidence, or why a defensible source is unavailable."></textarea></div>
</div></fieldset>
<div class="bottom"><button id="previous" type="button">← Previous</button><button id="nextIncomplete" type="button">Next incomplete</button><button id="next" type="button">Next →</button></div>
</section>
<section class="card" aria-label="Question navigation"><h3>Jump to a question</h3><p class="hint">Green = complete. The outlined number is the question you are viewing.</p><div class="nav-grid" id="questionNav"></div></section>
<footer class="footnote"><p><strong>Keep your download.</strong> Browser storage can be cleared or unavailable. Separate file copies may share browser storage; separate browser profiles or devices protect independent reviews.</p>
<button class="danger" id="clearButton" type="button" disabled>Clear this reviewer's saved draft…</button>
<details><summary>Packet identity</summary><p>Embedded data is the unchanged blinded packet and blank response template. This interface is a convenience layer; it creates no human-review results until a person enters them.</p><p id="packetHash" class="hash"></p><p id="templateHash" class="hash"></p></details></footer>
<noscript><p class="notice">Enable JavaScript to use this offline form. The original packet and JSONL response template remain available from the coordinator.</p></noscript>
</main>
<script id="reviewData" type="application/json">__REVIEW_DATA__</script>
<script>
'use strict';
(() => {
  const data = JSON.parse(document.getElementById('reviewData').textContent);
  const $ = id => document.getElementById(id);
  const answers = ['A','B','C','D','UNCERTAIN'];
  const applicability = [['DIRECT_SUPPORT','Direct support'],['PARTIAL_SUPPORT','Partial support'],['IRRELEVANT_OR_MISMATCHED','Irrelevant or mismatched'],['CONTRADICTORY','Contradictory'],['UNCERTAIN','Uncertain']];
  const ambiguity = [['CLEAR_SINGLE_ANSWER','Clear single answer'],['MULTIPLE_PLAUSIBLE_ANSWERS','Multiple plausible answers'],['NO_CORRECT_OPTION','No correct option'],['VERSION_DEPENDENT','Version dependent'],['UNCERTAIN','Uncertain']];
  let slot = '', position = 0, storageFailed = false;
  const today = () => { const d = new Date(); return [d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-'); };
  const blank = () => ({reviewer:'', date:today(), responses:data.template.map(row => ({...row}))});
  let state = blank();
  const key = () => 'cti-human-review-v1:' + data.packet_sha256 + ':' + encodeURIComponent(location.pathname) + ':reviewer-' + slot;
  const make = (tag, text, className) => { const element = document.createElement(tag); if (text !== undefined) element.textContent = text; if (className) element.className = className; return element; };
  const dateValid = () => /^\d{4}-\d{2}-\d{2}$/.test(state.date) && !Number.isNaN(Date.parse(state.date+'T00:00:00'));
  const complete = row => Boolean(state.reviewer.trim() && dateValid() && answers.includes(row.answer) && applicability.some(([v]) => v === row.applicability) && ambiguity.some(([v]) => v === row.ambiguity) && (row.citation.trim() || (row.answer === 'UNCERTAIN' && row.notes.trim())));
  const completed = () => state.responses.filter(complete).length;
  function status(text, error=false) { $('saveStatus').textContent = text; $('saveStatus').classList.toggle('error',error); }
  function save() {
    if (!slot) return;
    try { localStorage.setItem(key(),JSON.stringify(state)); storageFailed=false; status('Saved in this browser · reviewer '+slot); }
    catch (_error) { storageFailed=true; status('Browser saving unavailable. Download your draft frequently.',true); }
  }
  function restore() {
    state = blank();
    try {
      const raw = localStorage.getItem(key());
      if (!raw) { status('New draft · reviewer '+slot); return; }
      const saved = JSON.parse(raw);
      if (!saved || typeof saved.reviewer !== 'string' || typeof saved.date !== 'string' || !Array.isArray(saved.responses) || saved.responses.length !== data.packet.length) throw new Error('Invalid saved draft');
      state.reviewer = saved.reviewer.slice(0,200); state.date = saved.date;
      saved.responses.forEach((row,i) => {
        if (!row || row.review_id !== data.packet[i].review_id) throw new Error('Saved item mismatch');
        for (const field of ['answer','citation','applicability','ambiguity','notes']) {
          if (typeof row[field] !== 'string') throw new Error('Invalid response field');
          state.responses[i][field] = row[field];
        }
      });
      storageFailed=false; status('Restored your saved draft · reviewer '+slot);
    } catch (_error) {
      state=blank(); storageFailed=true;
      status('Saved draft could not be read. Existing storage was left in place; use your last download.',true);
    }
  }
  function progress() {
    const count = completed();
    $('progressText').textContent = count+' of '+data.packet.length+' complete';
    $('citationCount').textContent = state.responses.filter(row => row.citation.trim()).length+' citations supplied';
    $('progressFill').style.width = (100*count/data.packet.length)+'%';
    $('progressBar').setAttribute('aria-valuenow',String(count));
    $('nextIncomplete').disabled=!slot || count===data.packet.length;
    navButtons.forEach((button,i) => {
      const done = complete(state.responses[i]);
      button.classList.toggle('done',done); button.classList.toggle('current',i === position);
      button.setAttribute('aria-label','Question '+(i+1)+(done?', complete':', incomplete'));
      button.setAttribute('aria-current',i === position ? 'step' : 'false');
    });
  }
  function setField(field,value) { if (!slot) return; state.responses[position][field]=value; save(); progress(); $('exportMessage').textContent=''; }
  function render() {
    const item=data.packet[position], response=state.responses[position];
    $('position').textContent='Question '+(position+1)+' of '+data.packet.length;
    $('reviewId').textContent=item.review_id; $('questionHeading').textContent=item.question;
    $('optionList').replaceChildren();
    for (const letter of ['A','B','C','D']) {
      const row=make('div',undefined,'option'); row.append(make('span',letter,'letter'),make('span',item.options[letter],'option-text')); $('optionList').append(row);
    }
    $('evidenceDetails').open=false; $('evidenceList').replaceChildren();
    $('evidenceSummary').textContent='Retrieved evidence · '+item.evidence.length+' passages';
    item.evidence.forEach((fact,i) => { const section=make('div',undefined,'fact'); section.append(make('small','Passage '+(i+1)+' · '+fact.kind),make('p',fact.text)); $('evidenceList').append(section); });
    radioInputs.forEach(radio => { radio.checked=radio.value===response.answer; });
    for (const field of ['applicability','ambiguity','citation','notes']) $(field).value=response[field];
    $('previous').disabled=position===0; $('next').disabled=position===data.packet.length-1;
    $('nextIncomplete').disabled=!slot || completed()===data.packet.length;
    $('responseFields').disabled=!slot; $('startNotice').hidden=Boolean(slot);
    progress();
  }
  function go(index) { position=index; render(); $('questionHeading').focus({preventScroll:true}); $('questionHeading').scrollIntoView({behavior:'smooth',block:'start'}); }
  function selectOptions(id,values) {
    $(id).append(make('option','Choose a rating…')); $(id).children[0].value='';
    values.forEach(([value,label]) => { const option=make('option',label); option.value=value; $(id).append(option); });
    $(id).addEventListener('change',event => setField(id,event.target.value));
  }
  selectOptions('applicability',applicability); selectOptions('ambiguity',ambiguity);
  const radioInputs=answers.map(answer => {
    const label=make('label',undefined,'answer-option'), input=make('input');
    input.type='radio'; input.name='answer'; input.value=answer;
    input.addEventListener('change',() => { if (input.checked) setField('answer',answer); });
    label.append(input,make('span',answer==='UNCERTAIN'?'Uncertain':answer)); $('answerChoices').append(label); return input;
  });
  const navButtons=data.packet.map((_item,i) => { const button=make('button',String(i+1)); button.type='button'; button.addEventListener('click',() => go(i)); $('questionNav').append(button); return button; });
  $('reviewerSlot').addEventListener('change',event => {
    if (slot && !storageFailed) save();
    slot=['1','2'].includes(event.target.value)?event.target.value:''; position=0;
    if (slot) restore(); else { state=blank(); status('Choose your reviewer number to begin.'); }
    $('reviewerName').value=state.reviewer; $('reviewDate').value=state.date;
    for (const id of ['reviewerName','reviewDate','exportButton','clearButton']) $(id).disabled=!slot;
    $('exportMessage').textContent=''; render();
  });
  $('reviewerName').addEventListener('input',event => { state.reviewer=event.target.value; save(); progress(); });
  $('reviewDate').addEventListener('input',event => { state.date=event.target.value; save(); progress(); });
  for (const field of ['citation','notes']) $(field).addEventListener('input',event => setField(field,event.target.value));
  $('previous').addEventListener('click',() => { if (position>0) go(position-1); });
  $('next').addEventListener('click',() => { if (position<data.packet.length-1) go(position+1); });
  $('nextIncomplete').addEventListener('click',() => { for (let offset=1;offset<=data.packet.length;offset++) { const index=(position+offset)%data.packet.length; if (!complete(state.responses[index])) { go(index); return; } } });
  function exportRows() {
    return state.responses.map(response => {
      const row={}; for (const field of data.fields) row[field]=field==='reviewer'?state.reviewer.trim():field==='date'?state.date:response[field]; return row;
    });
  }
  $('exportButton').addEventListener('click',() => {
    if (!slot) return;
    save(); const rows=exportRows();
    const blob=new Blob([rows.map(row => JSON.stringify(row)).join('\n')+'\n'],{type:'application/x-ndjson;charset=utf-8'});
    const url=URL.createObjectURL(blob), link=make('a'); link.href=url; link.download='human_review_reviewer_'+slot+'.jsonl';
    document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url),1000);
    $('exportMessage').textContent=(completed()===data.packet.length?'Completed response file downloaded.':'Draft downloaded: '+completed()+' of '+data.packet.length+' complete.')+' Keep this reviewer’s file separate until independent review is finished.';
  });
  $('clearButton').addEventListener('click',() => {
    if (!slot || !window.confirm('Clear all 50 responses and the name/date saved for reviewer '+slot+' in this browser? Download your draft first if you want to keep it. Other reviewer drafts and downloaded files will remain.')) return;
    try { localStorage.removeItem(key()); storageFailed=false; } catch (_error) { storageFailed=true; }
    state=blank(); position=0; $('reviewerName').value=''; $('reviewDate').value=state.date; $('exportMessage').textContent='';
    status(storageFailed?'Draft cleared on screen; browser storage could not be cleared.':'This reviewer’s local draft was cleared.',storageFailed); render();
  });
  $('packetHash').textContent='Packet SHA-256: '+data.packet_sha256;
  $('templateHash').textContent='Blank template SHA-256: '+data.template_sha256;
  $('reviewDate').value=state.date; render();
})();
</script>
</body></html>
'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet',type=Path,default=ROOT/'human_review_packet.jsonl')
    parser.add_argument('--template',type=Path,default=ROOT/'human_review_template.jsonl')
    parser.add_argument('--output',type=Path,default=ROOT/'human_review.html')
    args=parser.parse_args()
    print(json.dumps(build(args.packet,args.template,args.output),indent=2))
