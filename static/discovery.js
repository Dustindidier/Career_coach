/* Only an explicit Yes promotes researched listings into the application workspace. */
let discoveryFilter='pending',discoveryBusy=false;
function discoveryView(){
  const all=state.profile.discovery||[],items=all.filter(x=>(x.decision||'pending')===discoveryFilter),item=items[0];
  const list=a=>`<ul>${(a||[]).map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`;
  return `<section class="panel discovery"><div class="eyebrow">FIND YOUR NEXT MATCH</div><div class="row spread"><h2>Discover opportunities</h2><span class="pill">${all.filter(x=>(x.decision||'pending')==='pending').length} to review</span></div><p>Weigh the fit, then choose. A Yes adds the role to My opportunities and prepares drafts from your starting documents.</p><div class="actions" aria-label="Discovery filter">${[['pending','To review'],['accepted','Accepted'],['rejected','Passed']].map(([v,l])=>`<button class="quiet" data-discovery-filter="${v}" aria-pressed="${discoveryFilter===v}">${l} (${all.filter(x=>(x.decision||'pending')===v).length})</button>`).join('')}</div>${item?`<article class="discovery-card"><p class="small muted">${items.length} in this stack · Checked ${esc((item.verifiedAt||'').slice(0,10))}</p><h3>${esc(item.title)}</h3><p><strong>${esc(item.company)}</strong> · ${esc(item.location||'Location to confirm')}</p><p>${esc(item.schedule||'Schedule to confirm')} · ${esc(item.salary||'Pay not disclosed')}</p><div class="grid"><div><h4>Why it could fit</h4>${list(item.fitReasons)}</div><div><h4>What to weigh</h4>${list(item.concerns)}</div></div><details><summary>Read role and verification notes</summary><p class="pre">${esc(item.posting)}</p><p class="small muted">${esc(item.availabilityEvidence||'Recheck before applying.')}</p></details><p><a href="${esc(safeUrl(item.sourceUrl))}" target="_blank" rel="noopener noreferrer">View employer posting ↗</a></p><div class="actions">${discoveryFilter==='pending'?`<button data-discovery-yes="${esc(item.id)}">Yes — prepare materials</button><button class="quiet" data-discovery-no="${esc(item.id)}">No — pass</button>`:discoveryFilter==='rejected'?`<button data-discovery-undo="${esc(item.id)}">Reconsider</button>`:`<button data-discovery-open="${esc(item.jobId)}">Review materials</button>`}<button class="quiet" data-discovery-next="${esc(item.id)}" ${items.length<2?'disabled':''}>Next card</button></div>${item.materialsError?'<p>Draft preparation needs a retry in Tailored materials.</p>':''}</article>`:'<p class="muted">No roles waiting in this stack.</p>'}<details><summary>Add a researched batch</summary><p class="small muted">Import your job-finder research. Importing creates no tailored materials.</p><label>Research file<input id="discovery-import" type="file" accept=".json,application/json"></label></details></section>`;
}
function bindDiscovery(){
  const save=async()=>{if(await persist())render();};
  document.querySelectorAll('[data-discovery-filter]').forEach(b=>b.onclick=()=>{discoveryFilter=b.dataset.discoveryFilter;render();});
  for(const [action,decision] of [['no','rejected'],['undo','pending']])document.querySelectorAll(`[data-discovery-${action}]`).forEach(b=>b.onclick=async()=>{if(discoveryBusy||pending||blocked)return;state.profile.discovery.find(x=>x.id===b.dataset[action==='no'?'discoveryNo':'discoveryUndo']).decision=decision;await save();});
  document.querySelectorAll('[data-discovery-next]').forEach(b=>b.onclick=()=>{const a=state.profile.discovery,i=a.findIndex(x=>x.id===b.dataset.discoveryNext);a.push(...a.splice(i,1));render();});
  document.querySelectorAll('[data-discovery-open]').forEach(b=>b.onclick=()=>{activeJob=b.dataset.discoveryOpen;localSet('activeJob',activeJob);tailored=null;location.hash='tailoring';});
  document.querySelectorAll('[data-discovery-yes]').forEach(b=>b.onclick=async()=>{
    if(discoveryBusy||pending||blocked)return;discoveryBusy=true;b.disabled=true;
    const item=state.profile.discovery.find(x=>x.id===b.dataset.discoveryYes);
    try{
      let j=state.jobs.find(x=>canonicalKey(x.sourceUrl)===canonicalKey(item.sourceUrl));
      if(j){item.decision='accepted';item.jobId=j.id;await save();return;}
      j={id:uid(),company:item.company,title:item.title,sourceUrl:item.sourceUrl,posting:item.posting,stage:'Exploring',requirements:[],notes:'Accepted from Discover.\n'+item.concerns.join('\n'),discoveryId:item.id};
      state.jobs.push(j);item.decision='accepted';item.jobId=j.id;if(!await persist())return;
      try{const d=await api('/api/tailor',{jobId:j.id});j.materials={resume:d.resume,coverLetter:d.coverLetter,sourceDigest:d.sourceDigest,baseSources:d.baseSources,updatedAt:new Date().toISOString()};item.materialsError=false;if(!await persist())return;toast('Role added. Source-based drafts are ready to review.');}
      catch(error){item.materialsError=true;await persist();toast('Role added. Open Tailored materials to retry.');}
      render();
    }catch(error){toast(error.message);}finally{discoveryBusy=false;b.disabled=false;}
  });
  const input=document.querySelector('#discovery-import');if(input)input.onchange=async()=>{
    if(discoveryBusy||pending||blocked)return;
    try{const f=input.files[0];if(!f||f.size>700000)throw Error('Choose a research JSON file below 700 KB.');const rows=JSON.parse(await f.text());
      if(!Array.isArray(rows)||rows.length>100||!rows.every(x=>x&&['company','title','sourceUrl','posting'].every(k=>typeof x[k]==='string')&&canonicalKey(x.sourceUrl)&&['fitReasons','concerns'].every(k=>Array.isArray(x[k])&&x[k].every(v=>typeof v==='string'))))throw Error('Research needs employer links, descriptions, fit reasons and concerns.');
      const all=state.profile.discovery=state.profile.discovery||[];let count=0;
      for(const row of rows){const key=canonicalKey(row.sourceUrl);if(all.some(x=>canonicalKey(x.sourceUrl)===key)||state.jobs.some(x=>canonicalKey(x.sourceUrl)===key))continue;all.push({...row,id:uid(),decision:'pending'});count++;}
      if(await persist()){toast(`${count} researched roles added. No materials created.`);render();}
    }catch(error){toast(error.message);}
  };
}
