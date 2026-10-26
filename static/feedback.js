/* Shared ledger: imported suggestions remain proposed until the user activates them. */
function researchFeedbackView(){
  const rows=state.profile.researchFeedback||[];
  return `<section class="panel"><h2>Research feedback loop</h2><p>Save what should change in the next search. Share the research brief with a ChatGPT career conversation, then import its feedback file here. Imported suggestions need review.</p><div class="actions"><button id="research-context-export" class="quiet">Download research brief</button></div><form id="research-feedback-form" data-draft="research-feedback"><label>What should future research do differently?<textarea name="text" required maxlength="4000"></textarea></label><label>Source / conversation reference<input name="source" required maxlength="2000" placeholder="My feedback, or a conversation link and quote"></label><label>Whose statement?<select name="sourceType"><option value="user">My direct feedback</option><option value="conversation">Conversation summary</option><option value="assistant">Assistant suggestion</option><option value="other">Other source</option></select></label><button>Save for review</button></form><label>Import conversation feedback JSON<input id="research-feedback-import" type="file" accept=".json,application/json"></label><p class="small muted">A brief contains private preferences, confirmed facts and role decisions. Share only with the conversation you choose. New chats do not sync automatically.</p>${rows.map(r=>`<article class="check"><span class="pill">${esc(r.status)}</span><p class="pre">${esc(r.text)}</p><p class="small muted">${esc(r.sourceType)} · ${esc(r.source)} · ${esc(r.createdAt)}</p><div class="actions">${r.status!=='active'?`<button data-feedback-state="active" data-feedback-id="${esc(r.id)}">Use in future research</button>`:''}${r.status==='active'?`<button class="quiet" data-feedback-state="superseded" data-feedback-id="${esc(r.id)}">Retire preference</button>`:''}${r.status!=='dismissed'?`<button class="quiet" data-feedback-state="dismissed" data-feedback-id="${esc(r.id)}">Dismiss</button>`:''}</div></article>`).join('')||'<p class="muted">No research feedback saved yet.</p>'}</section>`;
}
function bindResearchFeedback(){
  const form=document.querySelector('#research-feedback-form');if(!form)return;
  form.onsubmit=async e=>{e.preventDefault();if(pending||blocked)return;const v=formValues(form),rows=state.profile.researchFeedback=state.profile.researchFeedback||[];if(rows.length>=500)return toast('Feedback limit reached. Export a backup before removing old records.');rows.push({...v,id:uid(),status:'proposed',createdAt:new Date().toISOString(),reviewedAt:''});if(await persist()){clearDraft('research-feedback');render();}};
  document.querySelectorAll('[data-feedback-state]').forEach(b=>b.onclick=async()=>{if(pending||blocked)return;const row=state.profile.researchFeedback.find(r=>r.id===b.dataset.feedbackId);row.status=b.dataset.feedbackState;row.reviewedAt=new Date().toISOString();if(await persist())render();});
  document.querySelector('#research-context-export').onclick=async()=>{if(pending||blocked)return toast('Save or resolve workspace changes first.');try{const r=await fetch('/api/research-context');if(!r.ok)throw Error('Research brief unavailable.');download('career-research-context.json',JSON.stringify(await r.json(),null,2));}catch(error){toast(error.message);}};
  document.querySelector('#research-feedback-import').onchange=async e=>{
    if(pending||blocked)return;
    try{
      const f=e.target.files[0];if(!f||f.size>700000)throw Error('Choose a feedback JSON file below 700 KB.');
      const bundle=JSON.parse(await f.text());
      if(bundle.kind!=='career-research-feedback'||bundle.schemaVersion!==1||!Array.isArray(bundle.feedback)||bundle.feedback.length>100)throw Error('Expected a version 1 career-research-feedback bundle with up to 100 items.');
      const rows=state.profile.researchFeedback||[],add=[];
      for(const r of bundle.feedback){
        if(!r||!['id','text','source','sourceType'].every(k=>typeof r[k]==='string')||!r.id.trim()||r.id.length>200||!r.text.trim()||r.text.length>4000||!r.source.trim()||r.source.length>2000||!['user','conversation','assistant','app','other'].includes(r.sourceType))throw Error('Each item needs id, text, source and a valid sourceType. Nothing imported.');
        const old=rows.find(x=>x.id===r.id)||add.find(x=>x.id===r.id);
        if(old){if(['text','source','sourceType'].some(k=>old[k]!==r[k]))throw Error('An existing feedback ID has different content. Use a new ID for a correction. Nothing imported.');continue;}
        add.push({id:r.id,text:r.text,source:r.source,sourceType:r.sourceType,status:'proposed',createdAt:new Date().toISOString(),reviewedAt:''});
      }
      if(rows.length+add.length>500)throw Error('Feedback limit is 500 records. Nothing imported.');
      state.profile.researchFeedback=[...rows,...add];if(await persist()){render();toast(`${add.length} feedback items imported for review.`);}
    }catch(error){toast(error.message);}
  };
}
