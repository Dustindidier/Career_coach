'use strict';
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const uid = () => crypto.randomUUID();
const STORAGE = 'nextchapter.v2.';
let state, revision, capabilities = {ai:false}, queue = Promise.resolve(), pending = 0, blocked = false;
let activeJob = '', editingStory = null, session = null, busy = false;
let localAvailable = true;
function localGet(key) { try { return JSON.parse(localStorage.getItem(STORAGE + key)); } catch { return null; } }
function localSet(key, value) { try { localStorage.setItem(STORAGE + key, JSON.stringify(value)); } catch { localAvailable = false; } }
function localRemove(key) { try { localStorage.removeItem(STORAGE + key); } catch { /* Browser storage may be disabled. */ } }
function toast(text) { $('#toast').textContent = text; $('#toast').style.display = 'block'; setTimeout(() => $('#toast').style.display = 'none', 4500); }
function status(text) { $('#save-status').textContent = text; $('#mobile-status').textContent = text; }
function job() { return state.jobs.find(j => j.id === activeJob) || state.jobs[0]; }
function entries() { return state.profile.entries || []; }
function title(text, description) { return `<div class="intro"><div class="eyebrow">Your next chapter</div><h1>${text}</h1><p class="muted">${description}</p></div>`; }
function download(name, body, type='application/json') { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([body], {type})); a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000); }
function exportWorkspace(body=state) { download('career-workspace-backup.json', JSON.stringify(body, null, 2)); }
async function api(path, body) {
  const response = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  if (!response.ok) throw Error(`Request failed (${response.status}). Your draft is preserved.`);
  return response.json();
}
function showConflict(text) {
  $('#sync-warning').hidden = false;
  $('#sync-warning').innerHTML = `<strong>${esc(text)}</strong><p>Your local copy is preserved on this device when browser storage is available. Download it before loading the latest version.</p><div class="actions"><button id="download-unsaved">Download my unsaved copy</button><button class="quiet" id="reload-workspace">Load latest server version</button></div>`;
  $('#download-unsaved').onclick = () => exportWorkspace();
  $('#reload-workspace').onclick = () => { if (confirm('Load the latest server copy? Download your unsaved copy first. Form drafts and your interview session stay on this device.')) { localRemove('pending'); location.reload(); } };
}
function persist() {
  localSet('pending', {baseRevision:revision, body:state});
  if (blocked) { status('Not saved — resolve the conflict above'); return Promise.resolve(false); }
  const snapshot = JSON.stringify(state);
  pending++;
  status('Saving…');
  const result = queue.then(async () => {
    if (blocked) { pending--; return false; }
    try {
      const response = await fetch('/api/workspace', {method:'PUT', headers:{'Content-Type':'application/json','If-Match':`"${revision}"`}, body:snapshot});
      if (response.status === 409 || response.status === 428) {
        blocked = true; showConflict('Another device has saved a newer version. Nothing was overwritten.'); return false;
      }
      if (!response.ok) throw Error();
      revision = Number(response.headers.get('ETag').replaceAll('"',''));
      return true;
    } catch {
      blocked = true; showConflict('Could not save to the server. Your changes remain in this browser.'); return false;
    } finally {
      pending--;
      if (blocked) { localSet('pending', {baseRevision:revision, body:state}); status('Not saved — action needed above'); }
      else if (!pending) { localRemove('pending'); status('● Saved to workspace'); }
      else localSet('pending', {baseRevision:revision, body:state});
    }
  });
  queue = result.catch(() => false);
  return result;
}
function formValues(form) {
  const values = Object.fromEntries(new FormData(form));
  form.querySelectorAll('input[type=checkbox][name]').forEach(e => values[e.name] = e.checked);
  return values;
}
function clearDraft(key) { localRemove('draft.' + key); }
function restoreDrafts() {
  let restored = false;
  document.querySelectorAll('form[data-draft]').forEach(form => {
    const draft = localGet('draft.' + form.dataset.draft);
    if (draft) {
      for (const [name, value] of Object.entries(draft.values || {})) {
        const field = form.elements.namedItem(name);
        if (field) { if (field.type === 'checkbox') field.checked = value === true; else field.value = value; }
      }
      restored = true;
    }
    form.addEventListener('input', () => {
      localSet('draft.' + form.dataset.draft, {values:formValues(form), at:new Date().toISOString()});
      $('#draft-status').textContent = localAvailable ? 'Unsubmitted form drafts are saved on this device.' : 'Device storage unavailable. Keep this tab open.';
    });
  });
  $('#draft-status').textContent = restored ? 'Recovered unsubmitted form drafts from this device.' : 'Form drafts stay on this device; submitted records sync across devices.';
}
function evidenceOptions(selected='') {
  return `<option value="">No evidence linked / gap</option>` + state.stories.map(s => `<option value="story:${esc(s.id)}" ${selected==='story:'+s.id?'selected':''}>Story: ${esc(s.title)}</option>`).join('') + entries().filter(e => e.confirmed).map(e => `<option value="fact:${esc(e.id)}" ${selected==='fact:'+e.id?'selected':''}>Confirmed ${esc(e.category.toLowerCase())}: ${esc(e.text.slice(0,100))}</option>`).join('');
}
function evidenceExists(id) { return id.startsWith('story:') ? state.stories.some(s => 'story:'+s.id === id) : entries().some(e => 'fact:'+e.id === id && e.confirmed); }
function suggestion(text) {
  const words = new Set(text.toLowerCase().match(/[a-z]{4,}/g) || []);
  const sources = [...state.stories.map(s => ({id:'story:'+s.id, name:s.title, text:[s.title,s.tags,s.situation,s.action,s.outcome].join(' ')})), ...entries().filter(e => e.confirmed).map(e => ({id:'fact:'+e.id, name:e.text, text:e.text}))];
  return sources.map(s => ({...s, score:new Set((s.text.toLowerCase().match(/[a-z]{4,}/g) || []).filter(w => words.has(w))).size})).filter(s => s.score>=2).sort((a,b) => b.score-a.score)[0];
}
function home() {
  const j=job(), reviewed=(j?.requirements || []).filter(r=>r.reviewed), linked=reviewed.filter(r=>evidenceExists(r.evidenceId));
  return title(`A new direction, ${esc(state.profile.name)}.`, 'Your clinical experience is the foundation. Build what comes next.') + `<div class="grid"><div><section class="panel hero"><div class="eyebrow">Your next best step</div><span class="pill">Free guided coach</span><span class="pill">Role-specific practice</span><h2>Bring your experience.<br>Find the words.</h2><p>Practice using your selected role, reviewed requirements, and real stories.</p><a class="button" href="#practice">Enter interview studio →</a></section><div class="cards"><a class="panel" href="#stories"><div class="number">${state.stories.length}</div>Reusable stories</a><a class="panel" href="#jobs"><div class="number">${state.jobs.length}</div>Opportunities</a><a class="panel" href="#profile"><div class="number">${entries().filter(e=>e.confirmed).length}</div>Confirmed facts</a></div><section class="panel"><h2>A small next step</h2><p>${!entries().some(e=>e.confirmed)?'Add and confirm a few career facts so your practice uses accurate evidence.':!state.stories.length?'Capture one real clinical story. You can refine it later.':!reviewed.length?'Review the requirements of your next role, then map your evidence.':'Rehearse a requirement with an evidence gap, then save what you learned.'}</p></section></div><div><section class="panel"><div class="eyebrow">In focus</div><h2>${esc(j?.title||'Add your next opportunity')}</h2><p class="muted">${esc(j?.company||'Your next chapter starts here')}</p><span class="pill">${esc(j?.stage||'Exploring')}</span><p>${reviewed.length} reviewed requirements · ${linked.length} linked to evidence</p><a href="#jobs">Open role & evidence map →</a></section><section class="panel"><h2>Your workspace is growing</h2><p>${state.sessions.length} saved answers, available across devices.</p><p class="small muted">No paid service is enabled. Guided practice and requirement extraction run without an AI subscription.</p><a href="#settings">Costs & AI options →</a></section></div></div>`;
}
function stories() {
  const s=state.stories.find(x=>x.id===editingStory) || {title:'',tags:'',situation:'',action:'',outcome:''};
  return title('Your experience, ready to tell.', 'Edit and reuse real examples across interviews and applications.') + `<div class="grid"><section class="panel"><h2>${editingStory?'Refine your story':'Add a story'}</h2><form id="story-form" data-draft="story-${esc(editingStory||'new')}"><label for="story-title">Story title</label><input id="story-title" name="title" required value="${esc(s.title)}" placeholder="Recognizing a safety concern"><label for="story-tags">Skills demonstrated</label><input id="story-tags" name="tags" value="${esc(s.tags)}" placeholder="Clinical judgment, communication"><label for="situation">Situation</label><textarea id="situation" name="situation" required placeholder="What happened? Omit patient-identifying details.">${esc(s.situation)}</textarea><label for="action">Your actions</label><textarea id="action" name="action" required placeholder="What did you personally do and why?">${esc(s.action)}</textarea><label for="outcome">Outcome and learning</label><textarea id="outcome" name="outcome" required placeholder="State only what you can substantiate.">${esc(s.outcome)}</textarea><div class="actions"><button>Save story</button>${editingStory?'<button type="button" class="quiet" id="cancel-story">Back to new story</button>':''}</div></form></section><section><label for="story-search">Find a story or skill</label><input id="story-search" type="search" placeholder="Search titles, skills, or details"><p id="story-count" class="small muted">${state.stories.length} stories</p>${state.stories.map(s=>`<article class="panel story-card" data-search="${esc([s.title,s.tags,s.situation,s.action,s.outcome].join(' ').toLowerCase())}"><h3>${esc(s.title)}</h3><p class="small muted">${esc(s.tags)}</p><strong>Situation</strong><p class="pre">${esc(s.situation)}</p><strong>Actions</strong><p class="pre">${esc(s.action)}</p><strong>Outcome & learning</strong><p class="pre">${esc(s.outcome)}</p><div class="actions"><button class="quiet" data-edit-story="${esc(s.id)}">Edit story</button><button class="quiet danger" data-delete-story="${esc(s.id)}">Delete</button></div></article>`).join('')||'<div class="panel empty">Start with a safety concern, competing priorities, or adapting to a new team.</div>'}</section></div>`;
}
const categories=['Experience','Education','Credential','Accomplishment','Preference','Skill'];
function factFields(e) { return `<label>Category<select name="category">${categories.map(c=>`<option ${e.category===c?'selected':''}>${c}</option>`).join('')}</select></label><label>Fact, goal, or preference<textarea name="text" required>${esc(e.text||'')}</textarea></label><label>Source<input name="source" value="${esc(e.source||'')}" placeholder="Resume, certificate, or your own account"></label><label><input type="checkbox" name="confirmed" ${e.confirmed?'checked':''}> I reviewed and confirm this item</label>`; }
function profile() {
  return title('Memory you can inspect.', 'Confirm facts individually. Keep goals and constraints separate from accomplishments.')+`<div class="grid"><div><section class="panel"><h2>Your direction</h2><form id="profile-form" data-draft="profile"><label for="name">Preferred name</label><input id="name" name="name" required value="${esc(state.profile.name)}"><label for="summary">Career direction</label><textarea id="summary" name="summary">${esc(state.profile.summary)}</textarea><details><summary>Earlier notes and context</summary><label for="facts">Legacy career notes</label><textarea id="facts" name="facts" rows="7">${esc(state.profile.facts)}</textarea><label><input type="checkbox" name="confirmed" ${state.profile.confirmed?'checked':''}> I have reviewed these earlier notes</label><p class="small muted">Retained for continuity. Structured facts below allow more precise use.</p></details><div class="actions"><button>Save direction</button></div></form></section><section class="panel"><h2>Add a career fact</h2><form id="fact-form" data-draft="fact-new">${factFields({})}<div class="actions"><button>Add to memory</button></div></form></section><section class="panel"><h2>Bring in resume text</h2><p class="small muted">Paste text or choose a .txt / .md file. Suggested facts stay unconfirmed until you review them. PDF/DOCX parsing is not included in this release.</p><input id="resume-file" type="file" accept=".txt,.md,text/plain"><form id="resume-form" data-draft="resume"><label for="resume-text">Resume text</label><textarea id="resume-text" name="text" required rows="8"></textarea><label>Source label<input name="source" value="Resume text"></label><div class="actions"><button>Preview suggested facts</button></div></form><div id="resume-preview"></div></section></div><section><div class="row spread"><h2>Individual facts</h2><span class="pill">${entries().filter(e=>e.confirmed).length} confirmed / ${entries().length}</span></div>${entries().map(e=>`<details class="panel"><summary><span class="pill">${e.confirmed?'Confirmed':'Needs review'}</span> ${esc(e.text.slice(0,95))}</summary><form class="fact-edit" data-id="${esc(e.id)}" data-draft="fact-${esc(e.id)}">${factFields(e)}<p class="small muted">Last reviewed: ${e.reviewedAt?esc(new Date(e.reviewedAt).toLocaleDateString()):'Not yet'}</p><div class="actions"><button>Save fact</button><button type="button" class="quiet danger" data-delete-fact="${esc(e.id)}">Delete</button></div></form></details>`).join('')||'<div class="panel empty">Add experience, credentials, skills, accomplishments, and preferences. Only confirmed facts are offered as evidence.</div>'}</section></div>`;
}
function requirementCard(j,r) {
  const suggested=!r.evidenceId?suggestion(r.text):null;
  const valid=evidenceExists(r.evidenceId);
  return `<form class="requirement panel" data-job="${esc(j.id)}" data-id="${esc(r.id)}" data-draft="req-${esc(r.id)}"><label>Source passage / requirement<textarea name="text" required>${esc(r.text)}</textarea></label><label>Type<select name="kind">${['Requirement','Preferred','Responsibility / logistics','Other'].map(k=>`<option ${r.kind===k?'selected':''}>${k}</option>`).join('')}</select></label><label><input type="checkbox" name="reviewed" ${r.reviewed?'checked':''}> I verified this against the posting</label><label>Evidence<select name="evidenceId">${evidenceOptions(r.evidenceId)}</select></label>${r.evidenceId&&!valid?'<p class="danger small">Linked evidence was removed or is no longer confirmed. Select current evidence.</p>':''}${suggested?`<p class="small">Possible text match: ${esc(suggested.name.slice(0,120))}. <button type="button" class="quiet" data-suggest="${esc(suggested.id)}">Select suggestion</button></p>`:''}<label>Gap, clarification, or explanation<textarea name="note" placeholder="What still needs learning or verification?">${esc(r.note)}</textarea></label><div class="actions"><button>Save mapping</button><button type="button" class="quiet danger" data-delete-req="${esc(r.id)}" data-job="${esc(j.id)}">Remove</button></div></form>`;
}
function jobs() {
  return title('Understand the role. Show your evidence.', 'Review the posting, identify gaps, and connect requirements to real experience.')+`<div class="notice">Free extraction uses text rules. Suggestions can miss or misclassify requirements. Review them before practice; evidence links are your assessment, not a qualification guarantee.</div><form id="job-form" class="panel" data-draft="job-new"><h2>Add an opportunity</h2><div class="two"><label>Company<input name="company" required></label><label>Role title<input name="title" required></label></div><label>Source URL<input name="sourceUrl" type="url" placeholder="https://company.example/careers/role"></label><label>Actual posting text<textarea name="posting" placeholder="Paste the job description; a URL alone cannot be analyzed."></textarea></label><div class="actions"><button>Add opportunity</button></div></form>${state.jobs.map(j=>`<details class="panel job-card" ${j.id===job()?.id?'open':''}><summary><span class="pill">${esc(j.stage)}</span> ${esc(j.title)} · ${esc(j.company)}</summary><div class="actions"><button class="quiet" data-practice-job="${esc(j.id)}">Practice this role →</button><button class="quiet" data-worksheet="${esc(j.id)}">Export evidence worksheet</button></div><form class="job-edit" data-id="${esc(j.id)}" data-draft="job-${esc(j.id)}"><div class="two"><label>Company<input name="company" required value="${esc(j.company)}"></label><label>Role title<input name="title" required value="${esc(j.title)}"></label></div><label>Stage<select name="stage">${['Exploring','Applied','Interviewing','Offer','Closed'].map(x=>`<option ${j.stage===x?'selected':''}>${x}</option>`).join('')}</select></label><label>Source URL<input name="sourceUrl" type="url" value="${esc(j.sourceUrl||'')}"></label><label>Posting text<textarea name="posting" rows="6">${esc(j.posting)}</textarea></label><label>Notes, interview debrief & next steps<textarea name="notes">${esc(j.notes)}</textarea></label><div class="actions"><button>Save role</button><button type="button" class="quiet analyze" data-job="${esc(j.id)}">Extract requirements</button><button type="button" class="quiet danger" data-delete-job="${esc(j.id)}">Delete role</button></div></form><hr><h2>Requirement → evidence map</h2><p class="small muted">${(j.requirements||[]).filter(r=>r.reviewed).length} reviewed · ${(j.requirements||[]).filter(r=>r.reviewed&&evidenceExists(r.evidenceId)).length} linked to evidence. Text-match suggestions require your review.</p>${(j.requirements||[]).map(r=>requirementCard(j,r)).join('')||'<p class="muted">Extract source passages or add a requirement manually.</p>'}<form class="add-requirement" data-job="${esc(j.id)}" data-draft="req-new-${esc(j.id)}"><label>Add a requirement manually<textarea name="text" required></textarea></label><button>Add for review</button></form></details>`).join('')}`;
}
function practice() {
  const inProgress=session && !session.complete;
  return title('A conversation with a purpose.', 'Practice your selected role and reviewed requirements. Your answers become reusable memory.')+`<div class="grid"><section class="panel"><form id="practice-setup" data-draft="practice-setup"><label for="practice-job">Opportunity</label><select name="jobId" id="practice-job">${state.jobs.map(j=>`<option value="${esc(j.id)}" ${j.id===job()?.id?'selected':''}>${esc(j.company)} · ${esc(j.title)}</option>`).join('')||'<option value="">General career practice</option>'}</select><label>Requirement to rehearse<select name="focus" id="practice-focus"><option value="">General role preparation</option>${(job()?.requirements||[]).filter(r=>r.reviewed).map(r=>`<option value="${esc(r.text)}">${esc(r.text.slice(0,140))}</option>`).join('')}</select></label><div class="two"><label>Focus<select name="mode"><option value="recruiter">Recruiter rehearsal</option><option value="behavioral">Behavioral stories</option><option value="safety">Safety fundamentals</option><option value="negotiation">Negotiation practice</option></select></label><label>Format<select name="format"><option value="coaching">Coaching: feedback each turn</option><option value="simulation">Simulation: review at the end</option></select></label></div><label>Coach<select name="engine"><option value="guided">Free guided coach — no API or subscription</option>${capabilities.ai?'<option value="gemini">Gemini AI — uses configured provider account</option>':''}</select></label><p class="small muted">Guided mode adapts prompts to the role and selected requirement using rules. It is not an AI conversation. ${capabilities.ai?'AI mode sends the chosen role, confirmed facts, stories, and session to Gemini. Provider terms and quotas apply.':'AI is optional and not connected. See Costs & AI options.'}</p><div class="actions"><button ${busy?'disabled':''}>${inProgress?'Start a different session':'Start practice →'}</button></div></form><div id="exercise">${session?sessionView():''}</div></section><div><section class="panel"><h2>Your evidence nearby</h2>${state.stories.slice(0,5).map(s=>`<details><summary>${esc(s.title)}</summary><p class="pre">${esc(s.action)}</p><p class="pre">${esc(s.outcome)}</p></details>`).join('')||'<p class="muted">Add a real story to build your evidence library.</p>'}<p><a href="#stories">Open story bank →</a></p></section><section class="panel"><h2>Recent answers</h2>${state.sessions.slice(-8).reverse().map(s=>`<details><summary>${esc(s.question)}</summary><p class="pre">${esc(s.answer)}</p><p class="small muted">${esc(new Date(s.date).toLocaleString())} · ${esc(state.jobs.find(j=>j.id===s.jobId)?.company||'General / archived role')}</p>${(s.feedback||[]).map(x=>`<p class="small">${esc(x)}</p>`).join('')}</details>`).join('')||'<p class="muted">Submitted answers are saved across devices.</p>'}</section></div></div>`;
}
function sessionView() {
  const s=session, j=state.jobs.find(x=>x.id===s.jobId);
  if(s.complete) return `<hr><div class="eyebrow">Session complete</div><h2>Your practice, ready to revisit.</h2><p>${s.history.length} answers in this session for ${esc(j?.company||'general practice')}.</p>${s.history.map(h=>`<details class="panel"><summary>${esc(h.question)}</summary><p class="pre">${esc(h.answer)}</p><div class="feedback">${esc((h.feedback||[]).join('\n\n'))}</div></details>`).join('')}<label>One thing to improve next</label><form id="reflection-form" data-draft="reflection-${esc(s.id)}"><textarea name="reflection">${esc(s.reflection||'')}</textarea><div class="actions"><button>Save reflection</button></div></form>`;
  const response=s.response;
  return `<hr><div class="eyebrow">${esc(response.label)}</div><p class="small muted">${esc(j?.company||'General practice')} · ${esc(j?.title||'Career transition')} · ${s.format==='simulation'?'Simulation':'Coaching'}</p>${response.warning?`<div class="notice">${esc(response.warning)}</div>`:''}${s.format==='coaching'&&response.feedback?.length?`<div class="feedback">${esc(response.feedback.join('\n\n'))}</div>`:''}<div class="question">${esc(response.question)}</div><form id="answer-form"><label for="answer">Your answer · question ${s.turn+1}</label><textarea id="answer" name="answer" rows="7" required placeholder="Use your own experience. Avoid patient-identifying details.">${esc(s.answer||'')}</textarea><div class="actions"><button ${busy?'disabled':''}>${busy?'Working…':s.format==='simulation'?'Submit & continue':'Get feedback & continue'}</button><button type="button" class="quiet" id="dictate">Use voice dictation</button><button type="button" class="quiet" id="finish-session" ${busy?'disabled':''}>Finish & review</button></div></form><p class="small muted">Unsubmitted answers recover on this device only. Submit to save across devices. Browser dictation may use its speech provider.</p>`;
}
function settings() {
  return title('Free by default. Clear about the options.', 'Your current guided workflow needs no paid plugin or AI subscription.')+`<div class="grid"><div><section class="panel"><span class="pill">Enabled · $0 in AI usage</span><h2>Free guided coach</h2><p>Role-specific prompts, requirement-based questions, structure checkpoints, and coaching / simulation formats. Uses rules, not a language model.</p><p>Memory, story editing, evidence mapping, and text extraction also run without a paid API.</p></section><section class="panel"><span class="pill">${capabilities.ai?'Configured':'Optional · not connected'}</span><h2>Gemini AI coach</h2><p>Enables conversational follow-ups and answer-specific feedback. Gemini offers a free tier for eligible models/accounts, with quotas and provider data-use terms. Free availability is not guaranteed.</p><p>To stay free: use an eligible free-tier project, leave billing disabled, and set its API key securely as GEMINI_API_KEY on Render. Never paste it into this app or GitHub. If it fails or hits quota, the app falls back to guided mode.</p><p class="small muted">AI mode sends the selected posting, confirmed career facts, stories, and session answers to Google. Use it only if comfortable with the provider’s terms. No provider calls happen in guided mode.</p><p><a href="https://ai.google.dev/gemini-api/docs/pricing" target="_blank" rel="noopener noreferrer">Check current free-tier availability and pricing ↗</a></p></section><section class="panel"><h2>Paid options — not enabled</h2><p>A paid model account, realtime voice, or always-on hosting could improve capacity or latency. None is required. The free alternatives are guided coaching, browser dictation, and the existing free hosting plans.</p></section></div><div><section class="panel"><h2>Backups and device drafts</h2><p>Submitted records live in your shared database. Unsubmitted forms and interview progress are cached in this browser, in plaintext. Avoid shared devices and patient-identifying information.</p><button id="settings-export">Export workspace</button><label for="import">Restore JSON backup</label><input id="import" type="file" accept="application/json"><p class="small muted">Restore replaces the workspace only if no newer server version exists. Export first.</p><button id="clear-drafts" class="quiet danger">Clear drafts on this device</button></section><section class="panel"><h2>Practice history</h2><p>${state.sessions.length} submitted answers</p><button id="clear-history" class="quiet danger">Delete saved practice history</button></section></div></div>`;
}
function integrations() {
  const sources=state.profile.sources||[];
  return title('Keep the search connected.', 'Bring recruiter context and job alerts into the same workspace.')+`<div class="notice">Gmail connection in this chat and ongoing Gmail sync in the hosted app are separate. Hosted OAuth and scheduled sync are not connected yet. No emails are sent and no websites are scraped.</div><div class="grid"><div><section class="panel"><div class="eyebrow">Recruiter context</div><h2>Import an email for an opportunity</h2><p class="small muted">Until hosted Gmail sync is configured, paste a relevant email. Keep only the context you need; avoid forwarding unrelated personal information.</p><form id="email-form" data-draft="email-import"><label>Opportunity<select name="jobId" required>${state.jobs.map(j=>`<option value="${esc(j.id)}">${esc(j.company)} · ${esc(j.title)}</option>`).join('')||'<option value="">Add an opportunity first</option>'}</select></label><label>Sender<input name="from" required placeholder="Recruiter name or email"></label><label>Subject<input name="subject" required></label><label>Date / time, if known<input name="receivedAt" placeholder="Include time zone if relevant"></label><label>Message text<textarea name="body" required rows="7"></textarea></label><button ${state.jobs.length?'':'disabled'}>Save email context</button></form></section><section class="panel"><h2>Job sourcing watchlist & employer feeds</h2><p>Save employer career pages, job boards, and search links. Bookmarks open manually. Supported public employer feeds can fetch matching listings on demand; background scheduling is not enabled.</p><form id="source-form" data-draft="source-new"><label>Source name<input name="name" required placeholder="Employer careers or LinkedIn alert"></label><label>Search or careers URL<input name="url" type="url" required placeholder="https://..."></label><label>Source type<select name="provider"><option value="manual">Bookmark / job-board alert</option><option value="greenhouse">Greenhouse public employer feed</option><option value="lever">Lever public employer feed</option></select></label><label>Employer board slug (for feeds only)<input name="board" placeholder="Employer slug from its public job-board URL"></label><label>Search focus / feed keywords<textarea name="query" placeholder="Role titles, location, remote preference, and alert cadence"></textarea></label><button>Add source</button></form>${sources.map(s=>`<article class="check"><strong>${esc(s.name)}</strong><p class="pre small">${esc(s.query)}</p><a href="${esc(safeUrl(s.url))}" target="_blank" rel="noopener noreferrer">Open source ↗</a> ${s.provider&&s.provider!=='manual'?`<button class="quiet" data-fetch-source="${esc(s.id)}">Fetch listings</button>`:''} <button class="quiet danger" data-delete-source="${esc(s.id)}">Remove</button></article>`).join('')}</section></div><div><section class="panel"><h2>Free sourcing routes</h2><p><a href="https://www.linkedin.com/jobs/" target="_blank" rel="noopener noreferrer">LinkedIn Jobs ↗</a></p><p><a href="https://www.indeed.com/" target="_blank" rel="noopener noreferrer">Indeed ↗</a></p><p><a href="https://www.glassdoor.com/Job/" target="_blank" rel="noopener noreferrer">Glassdoor ↗</a></p><p><a href="https://www.ziprecruiter.com/" target="_blank" rel="noopener noreferrer">ZipRecruiter ↗</a></p><p class="small muted">Create job alerts on the sites you use. Gmail alert ingestion can later consolidate them without automated account scraping. Public employer feeds and supported ATS endpoints are another route.</p></section><section class="panel"><h2>Next integration steps</h2><p>1. Connect Gmail with read access to relevant messages and permission to create drafts.</p><p>2. Review suggested matches to opportunities and extracted dates before saving.</p><p>3. Add scheduled checks using a free scheduler within provider quotas.</p><p>4. Keep sending messages and submitting applications behind your review.</p><p class="small muted">Paid job-data APIs are optional; free alternatives are alerts, supported employer feeds, and manual import. Current app: no scheduler or mailbox tokens stored.</p></section></div></div><section class="panel"><h2>Sourcing inbox</h2><p class="small muted">Feed matches are suggestions, not verified fits. Review the original posting before adding a role. Fetching a feed never submits an application.</p>${(state.profile.inbox||[]).map(item=>`<article class="check"><h3>${esc(item.title)}</h3><p>${esc(item.company)} · ${esc(item.location||'Location not specified')}</p><a href="${esc(safeUrl(item.sourceUrl))}" target="_blank" rel="noopener noreferrer">Original posting ↗</a><details><summary>Review description</summary><p class="pre">${esc(item.posting)}</p></details><div class="actions"><button data-add-listing="${esc(item.id)}">Add to opportunities</button><button class="quiet" data-dismiss-listing="${esc(item.id)}">Dismiss</button></div></article>`).join('')||'<p class="muted">Fetch a supported employer feed to collect candidates here.</p>'}</section>${state.jobs.map(j=>`<section class="panel"><h2>${esc(j.company)} · Communications</h2>${(j.communications||[]).map(m=>`<details><summary>${esc(m.subject)} · ${esc(m.from)}</summary><p class="small muted">${esc(m.receivedAt||'Date not recorded')} · Manually imported</p><p class="pre">${esc(m.body)}</p><button class="quiet danger" data-delete-email="${esc(m.id)}" data-job="${esc(j.id)}">Remove email context</button></details>`).join('')||'<p class="muted">No email context added.</p>'}<form class="reply-form" data-job="${esc(j.id)}" data-draft="reply-${esc(j.id)}"><label>Reply purpose<select name="purpose"><option value="followup">Interview follow-up</option><option value="schedule">Confirm scheduling</option><option value="negotiate">Discuss compensation</option></select></label><button type="button" class="quiet create-reply">Start a reply template</button><label>Reviewable email draft<textarea name="replyDraft" rows="8">${esc(j.replyDraft||'')}</textarea></label><div class="actions"><button>Save draft to workspace</button><button type="button" class="quiet download-reply">Download draft</button></div><p class="small muted">Templates use placeholders; fill them with verified details. Saved here only, not in Gmail. Nothing is sent.</p></form></section>`).join('')}`;
}
function safeUrl(value) { try { const url=new URL(value); return ['https:','http:'].includes(url.protocol)?url.href:'#'; } catch { return '#'; } }
function worksheet(id) {
  const j=state.jobs.find(x=>x.id===id);
  const lines=[`# ${j.title} — ${j.company}`,`Source: ${j.sourceUrl||'Not recorded'}`,`## Posting\n${j.posting||'Not added'}`,'## Reviewed career facts',...entries().filter(e=>e.confirmed).map(e=>`- ${e.category}: ${e.text} (source: ${e.source||'Your account'})`),'## Requirement → evidence map',...(j.requirements||[]).map(r=>`- [${r.reviewed?'Reviewed':'Unreviewed'}] ${r.text}\n  Evidence: ${r.evidenceId||'Gap / not linked'}\n  Notes: ${r.note}`),'## Story library',...state.stories.map(s=>`### ${s.title}\nSituation: ${s.situation}\nActions: ${s.action}\nOutcome: ${s.outcome}`),`## Opportunity notes\n${j.notes}`];
  download('career-evidence-worksheet.md',lines.join('\n\n'),'text/markdown');
}
function saveSession() { localSet('session',session); }
function coachPayload(answer='', turn=0) {
  const j=state.jobs.find(x=>x.id===session.jobId);
  return {mode:session.mode, engine:session.engine, turn, answer, job:j||{}, focus:session.focus||'', facts:entries().filter(e=>e.confirmed), stories:state.stories, history:session.history.slice(-6)};
}
async function startPractice(form) {
  if(busy) return;
  if(session&&!session.complete&&!confirm('Start another session? Your current unsubmitted answer will be replaced. Submitted answers remain saved.'))return;
  const v=formValues(form);
  if(v.engine==='gemini'&&!confirm('Send this role (including imported email context), confirmed facts, story library, and session to Google for AI coaching? Provider data-use terms apply.'))return;
  const previous=session;
  session={id:uid(),jobId:v.jobId,mode:v.mode,engine:v.engine,format:v.format,focus:v.focus||'',history:[],turn:0,answer:'',complete:false};
  activeJob=v.jobId;localSet('activeJob',activeJob);busy=true;
  form.querySelector('button').disabled=true;
  try { session.response=await api('/api/coach',coachPayload());saveSession();clearDraft('practice-setup'); }
  catch(e){session=previous;toast(e.message);}
  finally{busy=false;render();}
}
async function submitAnswer(form) {
  if(busy)return;
  const answer=form.elements.answer.value.trim();if(!answer)return;
  busy=true;session.answer=answer;saveSession();form.querySelector('button').disabled=true;
  try {
    const response=await api('/api/coach',coachPayload(answer,session.turn+1));
    const item={id:uid(),sessionId:session.id,jobId:session.jobId,mode:session.mode,question:session.response.question,answer,date:new Date().toISOString(),feedback:response.feedback||[],engine:response.engine};
    state.sessions.push(item);
    session.history.push(item);session.turn++;session.answer='';session.response=response;session.complete=response.complete;saveSession();
    await persist();
  } catch(e){toast(e.message);}
  finally{busy=false;render();}
}
function dictate() {
  const Speech=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!Speech)return toast('Dictation is unavailable in this browser. Typed practice works everywhere.');
  if(!confirm('Your browser may send audio to its speech provider. Continue?'))return;
  const recognition=new Speech();recognition.lang='en-US';
  $('#dictate').textContent='Listening…';
  recognition.onresult=e=>{if($('#answer')){$('#answer').value+=' '+e.results[0][0].transcript;session.answer=$('#answer').value;saveSession();}};
  recognition.onerror=()=>toast('Dictation failed. Please type your answer.');
  recognition.onend=()=>{if($('#dictate'))$('#dictate').textContent='Use voice dictation';};
  recognition.start();
}
function bindStories() {
  $('#story-form').onsubmit=async e=>{
    e.preventDefault();const form=e.target,values=formValues(form);
    if(editingStory)Object.assign(state.stories.find(s=>s.id===editingStory),values,{updatedAt:new Date().toISOString()});
    else state.stories.push({id:uid(),...values,updatedAt:new Date().toISOString()});
    clearDraft(form.dataset.draft);editingStory=null;await persist();render();
  };
  if($('#cancel-story'))$('#cancel-story').onclick=()=>{editingStory=null;render();};
  $('#story-search').oninput=e=>{const query=e.target.value.toLowerCase();let count=0;document.querySelectorAll('.story-card').forEach(card=>{card.hidden=!card.dataset.search.includes(query);if(!card.hidden)count++;});$('#story-count').textContent=`${count} matching stories`;};
  document.querySelectorAll('[data-edit-story]').forEach(b=>b.onclick=()=>{editingStory=b.dataset.editStory;render();$('#story-title').focus();});
  document.querySelectorAll('[data-delete-story]').forEach(b=>b.onclick=async()=>{if(confirm('Delete this story? Requirement maps will show its evidence as missing.')){state.stories=state.stories.filter(s=>s.id!==b.dataset.deleteStory);clearDraft('story-'+b.dataset.deleteStory);if(editingStory===b.dataset.deleteStory)editingStory=null;await persist();render();}});
}
function bindProfile() {
  $('#profile-form').onsubmit=async e=>{e.preventDefault();Object.assign(state.profile,formValues(e.target));clearDraft('profile');if(await persist())toast('Career direction saved');};
  $('#fact-form').onsubmit=async e=>{e.preventDefault();const v=formValues(e.target);state.profile.entries=entries();state.profile.entries.push({id:uid(),...v,reviewedAt:v.confirmed?new Date().toISOString():''});clearDraft('fact-new');await persist();render();};
  document.querySelectorAll('.fact-edit').forEach(form=>form.onsubmit=async e=>{e.preventDefault();const v=formValues(form);Object.assign(entries().find(x=>x.id===form.dataset.id),v,{reviewedAt:v.confirmed?new Date().toISOString():''});clearDraft(form.dataset.draft);await persist();render();});
  document.querySelectorAll('[data-delete-fact]').forEach(b=>b.onclick=async()=>{if(confirm('Delete this fact? Linked requirements will show missing evidence.')){state.profile.entries=entries().filter(e=>e.id!==b.dataset.deleteFact);clearDraft('fact-'+b.dataset.deleteFact);await persist();render();}});
  $('#resume-file').onchange=async e=>{const f=e.target.files[0];if(!f)return;if(f.size>200000||!(/\.(txt|md)$/i.test(f.name)))return toast('Choose a .txt or .md file under 200 KB.');$('#resume-text').value=await f.text();$('#resume-text').dispatchEvent(new Event('input',{bubbles:true}));};
  $('#resume-form').onsubmit=e=>{
    e.preventDefault();const v=formValues(e.target),lines=[...new Set(v.text.split(/\n+/).map(x=>x.trim()).filter(x=>x.length>=12&&x.length<=700))].slice(0,30);
    $('#resume-preview').innerHTML=lines.length?`<p class="small muted">Select lines worth saving. Each will enter memory unconfirmed; review category and accuracy afterward.</p><form id="candidate-facts">${lines.map((x,i)=>`<label><input type="checkbox" name="line" value="${i}" checked> ${esc(x)}</label>`).join('')}<button>Add selected candidates</button></form>`:'<p>No suitable lines found. Paste one statement per line.</p>';
    if($('#candidate-facts'))$('#candidate-facts').onsubmit=async event=>{event.preventDefault();const selected=new FormData(event.target).getAll('line').map(Number);state.profile.entries=entries();let added=0;for(const index of selected){if(!entries().some(x=>x.text===lines[index])){state.profile.entries.push({id:uid(),category:'Experience',text:lines[index],source:v.source||'Resume text',confirmed:false,reviewedAt:''});added++;}}clearDraft('resume');if(await persist())toast(`${added} candidates added for review`);render();};
  };
}
function bindJobs() {
  $('#job-form').onsubmit=async e=>{e.preventDefault();const j={id:uid(),stage:'Exploring',notes:'',requirements:[],...formValues(e.target)};state.jobs.push(j);activeJob=j.id;localSet('activeJob',activeJob);clearDraft('job-new');await persist();render();};
  document.querySelectorAll('.job-edit').forEach(form=>{
    form.onsubmit=async e=>{e.preventDefault();Object.assign(state.jobs.find(j=>j.id===form.dataset.id),formValues(form));clearDraft(form.dataset.draft);if(await persist())toast('Role updated');};
    form.querySelector('.analyze').onclick=async e=>{
      const j=state.jobs.find(j=>j.id===form.dataset.id),v=formValues(form);
      if(!v.posting.trim())return toast('Paste the actual posting text first.');
      if(j.requirements?.length&&!confirm('Replace the existing requirement map? Export the evidence worksheet first if you want to keep it.'))return;
      e.target.disabled=true;
      try {const result=await api('/api/analyze',{posting:v.posting});Object.assign(j,v,{requirements:result.requirements});clearDraft(form.dataset.draft);await persist();toast(result.requirements.length?'Extracted passages are ready for review.':'No passages matched. Add requirements manually.');render();}
      catch(error){toast(error.message);e.target.disabled=false;}
    };
  });
  document.querySelectorAll('.requirement').forEach(form=>{
    form.onsubmit=async e=>{e.preventDefault();const j=state.jobs.find(j=>j.id===form.dataset.job);Object.assign(j.requirements.find(r=>r.id===form.dataset.id),formValues(form));clearDraft(form.dataset.draft);if(await persist())toast('Evidence mapping saved');};
    const button=form.querySelector('[data-suggest]');if(button)button.onclick=()=>{form.elements.evidenceId.value=button.dataset.suggest;form.elements.evidenceId.dispatchEvent(new Event('input',{bubbles:true}));};
  });
  document.querySelectorAll('.add-requirement').forEach(form=>form.onsubmit=async e=>{e.preventDefault();const j=state.jobs.find(j=>j.id===form.dataset.job);j.requirements=j.requirements||[];j.requirements.push({id:uid(),text:form.elements.text.value,kind:'Requirement',reviewed:false,evidenceId:'',note:''});clearDraft(form.dataset.draft);await persist();render();});
  document.querySelectorAll('[data-delete-req]').forEach(b=>b.onclick=async()=>{if(confirm('Remove this requirement?')){const j=state.jobs.find(j=>j.id===b.dataset.job);j.requirements=j.requirements.filter(r=>r.id!==b.dataset.deleteReq);clearDraft('req-'+b.dataset.deleteReq);await persist();render();}});
  document.querySelectorAll('[data-practice-job]').forEach(b=>b.onclick=()=>{activeJob=b.dataset.practiceJob;localSet('activeJob',activeJob);clearDraft('practice-setup');location.hash='practice';});
  document.querySelectorAll('[data-worksheet]').forEach(b=>b.onclick=()=>worksheet(b.dataset.worksheet));
  document.querySelectorAll('[data-delete-job]').forEach(b=>b.onclick=async()=>{if(confirm('Delete this role, its email context, and maps? Saved interview answers remain.')){state.jobs=state.jobs.filter(j=>j.id!==b.dataset.deleteJob);clearDraft('job-'+b.dataset.deleteJob);await persist();render();}});
}
function bindPractice() {
  $('#practice-setup').onsubmit=e=>{e.preventDefault();startPractice(e.target);};
  $('#practice-job').onchange=e=>{const j=state.jobs.find(j=>j.id===e.target.value);$('#practice-focus').innerHTML='<option value="">General role preparation</option>'+(j?.requirements||[]).filter(r=>r.reviewed).map(r=>`<option value="${esc(r.text)}">${esc(r.text.slice(0,140))}</option>`).join('');};
  if($('#answer-form')){
    $('#answer').oninput=e=>{session.answer=e.target.value;saveSession();$('#draft-status').textContent=localAvailable?'Answer draft saved on this device.':'Device storage unavailable. Keep this tab open.';};
    $('#answer-form').onsubmit=e=>{e.preventDefault();submitAnswer(e.target);};
    $('#dictate').onclick=dictate;
    $('#finish-session').onclick=()=>{if(session.answer&&!confirm('Finish without submitting the current answer? Copy it first if you want to keep it.'))return;session.complete=true;saveSession();render();};
  }
  if($('#reflection-form'))$('#reflection-form').onsubmit=async e=>{e.preventDefault();session.reflection=e.target.elements.reflection.value;saveSession();state.sessions.filter(s=>s.sessionId===session.id).forEach(s=>s.reflection=session.reflection);clearDraft(e.target.dataset.draft);if(await persist())toast('Reflection saved with your session answers');};
}
function bindSettings() {
  $('#settings-export').onclick=()=>exportWorkspace();
  $('#clear-drafts').onclick=()=>{if(confirm('Clear unsubmitted forms and the current interview session on this device? Pending unsaved workspace changes will be kept.')){try{for(const key of Object.keys(localStorage))if(key.startsWith(STORAGE+'draft.'))localStorage.removeItem(key);}catch{}localRemove('session');session=null;render();toast('Device drafts cleared');}};
  $('#clear-history').onclick=async()=>{if(confirm('Delete submitted practice history?')){state.sessions=[];localRemove('session');session=null;await persist();render();}};
  $('#import').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;if(file.size>2_000_000)throw Error();const imported=JSON.parse(await file.text());if(!validImport(imported))throw Error();if(confirm('Replace the current workspace with this backup? Export your current workspace first.')){state=imported;const ok=await persist();if(ok){session=null;localRemove('session');render();toast('Workspace restored');}}}catch{toast('Invalid backup. Choose a workspace JSON export.');}};
}
function bindIntegrations() {
  $('#email-form').onsubmit=async e=>{e.preventDefault();const v=formValues(e.target),j=state.jobs.find(j=>j.id===v.jobId);if(!j)return;j.communications=j.communications||[];j.communications.push({id:uid(),...v,source:'manual'});clearDraft('email-import');await persist();render();};
  $('#source-form').onsubmit=async e=>{e.preventDefault();const v=formValues(e.target);if(safeUrl(v.url)==='#')return toast('Use an http or https source URL.');state.profile.sources=state.profile.sources||[];state.profile.sources.push({id:uid(),...v});clearDraft('source-new');await persist();render();};
  document.querySelectorAll('[data-fetch-source]').forEach(b=>b.onclick=async()=>{
    const source=state.profile.sources.find(s=>s.id===b.dataset.fetchSource);b.disabled=true;
    try{const result=await api('/api/source-preview',{provider:source.provider,board:source.board,query:source.query});state.profile.inbox=state.profile.inbox||[];let count=0;for(const listing of result.jobs){if(!state.profile.inbox.some(x=>x.id===listing.id)&&!state.jobs.some(j=>j.sourceUrl&&j.sourceUrl===listing.sourceUrl)){state.profile.inbox.push({...listing,retrievedAt:new Date().toISOString()});count++;}}const ok=await persist();render();if(ok)toast(`${count} new listings added to the sourcing inbox`);}catch(error){toast(error.message);b.disabled=false;}
  });
  document.querySelectorAll('[data-add-listing]').forEach(b=>b.onclick=async()=>{const listing=state.profile.inbox.find(x=>x.id===b.dataset.addListing);const j={...listing,id:uid(),stage:'Exploring',notes:'Imported from a public employer feed. Verify current details and fit.',requirements:[]};state.jobs.push(j);state.profile.inbox=state.profile.inbox.filter(x=>x.id!==listing.id);activeJob=j.id;localSet('activeJob',activeJob);await persist();location.hash='jobs';});
  document.querySelectorAll('[data-dismiss-listing]').forEach(b=>b.onclick=async()=>{state.profile.inbox=state.profile.inbox.filter(x=>x.id!==b.dataset.dismissListing);await persist();render();});
  document.querySelectorAll('[data-delete-source]').forEach(b=>b.onclick=async()=>{if(confirm('Remove this source?')){state.profile.sources=state.profile.sources.filter(s=>s.id!==b.dataset.deleteSource);await persist();render();}});
  document.querySelectorAll('[data-delete-email]').forEach(b=>b.onclick=async()=>{if(confirm('Remove this email context?')){const j=state.jobs.find(j=>j.id===b.dataset.job);j.communications=j.communications.filter(m=>m.id!==b.dataset.deleteEmail);await persist();render();}});
  document.querySelectorAll('.reply-form').forEach(form=>{
    form.onsubmit=async e=>{e.preventDefault();state.jobs.find(j=>j.id===form.dataset.job).replyDraft=form.elements.replyDraft.value;clearDraft(form.dataset.draft);if(await persist())toast('Draft saved here. Nothing sent to Gmail.');};
    form.querySelector('.create-reply').onclick=()=>{
      if(form.elements.replyDraft.value&&!confirm('Replace the text with a new template?'))return;
      const j=state.jobs.find(j=>j.id===form.dataset.job),kind=form.elements.purpose.value;
      const templates={followup:`Hi [recruiter name],\n\nThank you for the conversation about the ${j.title} position at ${j.company}. I appreciated learning about [specific detail discussed].\n\n[One accurate connection to your experience or interest.]\n\nPlease let me know if I can provide anything further. I look forward to hearing about next steps.\n\nBest,\n${state.profile.name}`,schedule:`Hi [recruiter name],\n\nThank you for the invitation to discuss the ${j.title} position. I can confirm [date, time, and time zone].\n\nPlease let me know [any remaining logistics question].\n\nBest,\n${state.profile.name}`,negotiate:`Hi [recruiter name],\n\nThank you for the offer for the ${j.title} position. I am interested in the opportunity and appreciate the team's time.\n\nBefore deciding, could we discuss [base salary / benefits / schedule]? Based on [verified experience and actual priorities], I would like to explore [specific request].\n\nI would welcome a conversation about what flexibility is available.\n\nBest,\n${state.profile.name}`};form.elements.replyDraft.value=templates[kind];form.elements.replyDraft.dispatchEvent(new Event('input',{bubbles:true}));
    };
    form.querySelector('.download-reply').onclick=()=>download('email-draft.txt',form.elements.replyDraft.value,'text/plain');
  });
}
function validImport(x) {
  const strings=(o,keys)=>o&&typeof o==='object'&&keys.every(k=>typeof o[k]==='string');
  return x&&Object.keys(x).sort().join(',')==='jobs,profile,sessions,stories'&&strings(x.profile,['name','summary','facts'])&&typeof x.profile.confirmed==='boolean'&&['jobs','stories','sessions'].every(k=>Array.isArray(x[k]))&&x.jobs.every(j=>strings(j,['id','company','title','stage','posting','notes']))&&x.stories.every(s=>strings(s,['id','title','tags','situation','action','outcome']))&&x.sessions.every(s=>strings(s,['id','jobId','mode','question','answer','date']));
}
function render() {
  if(!state)return;
  const page=location.hash.slice(1)||'home';
  document.querySelectorAll('nav a').forEach(a=>a.classList.toggle('active',a.hash==='#'+page));
  $('#app').innerHTML=({home,stories,profile,jobs,practice,settings,integrations}[page]||home)();
  restoreDrafts();
  ({stories:bindStories,profile:bindProfile,jobs:bindJobs,practice:bindPractice,settings:bindSettings,integrations:bindIntegrations}[page]||(()=>{}))();
}
async function boot() {
  try {
    const response=await fetch('/api/workspace');if(!response.ok)throw Error();
    state=await response.json();const etag=response.headers.get('ETag');if(!etag)throw Error();revision=Number(etag.replaceAll('"',''));
    try{const r=await fetch('/api/capabilities');if(r.ok)capabilities=await r.json();}catch{}
    activeJob=localGet('activeJob')||state.jobs[0]?.id||'';session=localGet('session');if(session&&!session.response)session=null;
    const recovered=localGet('pending');
    if(recovered?.body){state=recovered.body;blocked=true;showConflict(recovered.baseRevision===revision?'An unsaved workspace copy was recovered on this device.':'Your recovered copy differs from the latest server version.');}
    render();status(blocked?'Unsaved copy recovered — action needed':'● Saved to workspace');
    if(recovered?.baseRevision===revision){
      const button=document.createElement('button');button.textContent='Save recovered copy';button.onclick=async()=>{blocked=false;$('#sync-warning').hidden=true;await persist();render();};$('#sync-warning .actions').append(button);
    }
  } catch {$('#app').innerHTML=title('Could not load your workspace.','Check your connection and reload. Existing device drafts have not been deleted.');status('Connection failed');}
}
window.addEventListener('hashchange',render);
window.addEventListener('beforeunload',event=>{if(pending||blocked||busy){event.preventDefault();event.returnValue='';}});
$('#export').onclick=()=>{if(state)exportWorkspace();};
boot();
