/* Evidence-based estimates, recomputed from current preferences. No provider calls. */
(function(root){
'use strict';
const DEFAULT_WEIGHTS={pay:5,advancement:5,interest:3,background:4,practical:3};
const LABELS={pay:'Pay goal',advancement:'Potential for advancement',interest:'Your interest',background:'Background & experience',practical:'Travel, location & work style'};
const clamp=n=>Math.max(0,Math.min(100,n));
const band=(low,high,reason,status='estimated',evidence=[])=>({low,high,reason,status,evidence});
const unknown=reason=>band(0,100,reason,'unknown');
function salaryGoals(profile){
  const text=profile.searchPreferences?.compensation||'';
  const read=word=>{const m=text.match(new RegExp('(?:'+word+')\\s*[:=]?\\s*\\$?\\s*([0-9][0-9,]*(?:\\.[0-9]+)?)\\s*(k)?','i'));return m?Number(m[1].replaceAll(',',''))*(m[2]?1000:1):null;};
  const target=read('target|goal'),minimum=read('minimum|min\\b|floor');
  return {target,minimum,text,valid:target>0&&minimum>0&&minimum<=target};
}
function payEvidence(record){
  const text=record.salary||record.careerPath?.steps?.[0]?.salary||'';
  if(!text||/undisclosed|not disclosed|not independently|not verified|pay needs confirmation|does not clearly distinguish|guaranteed base.*(?:unknown|undisclosed)/i.test(text))return null;
  if(/base\s*\+\s*(?:incentive|commission)|base\s+plus\s+(?:incentive|commission)|on.target earnings|\bOTE\b/i.test(text))return null;
  const values=[...text.matchAll(/\$\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(k)?/gi)].map(m=>Number(m[1].replaceAll(',',''))*(m[2]?1000:1));
  if(!values.length)return null;
  let low=values[0],high=values[1]||low;
  // Only the first range is pay; later numbers may be a minimum/negotiating target.
  const range=text.match(/\$\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(k)?\s*(?:–|—|-|to)\s*\$?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(k)?/i);
  if(range){low=Number(range[1].replaceAll(',',''))*(range[2]||range[4]&&Number(range[1].replaceAll(',',''))<1000?1000:1);high=Number(range[3].replaceAll(',',''))*(range[4]?1000:1);}
  else high=low;
  const hourly=/hour|\/hr/i.test(text)&&low<300;
  if(hourly){low*=2080;high*=2080;}
  if(high<low||low<=0)return null;
  return {low,high,estimated:hourly||/estimate|planning|indexed|third.party/i.test(text),hourly,text};
}
function family(record){
  const t=record.title.toLowerCase();
  if(/institutional review|\birb\b/.test(t))return 'regulatory';
  if(/clinical data|clinical safety|clinical research|clinical trial|trial navigator|field procedural/.test(t))return 'research';
  if(/clinical reviewer|quality|utilization|documentation|informatics/.test(t))return 'healthcare';
  if(/educator|education/.test(t))return 'education';
  if(/sales|territory|therapy development|account/.test(t))return 'commercial';
  if(/clinical specialist|clinical solution/.test(t))return 'device';
  return 'unknown';
}
function interests(profile){return (profile.searchPreferences?.roles||[]).join(' ').toLowerCase();}
function payScore(record,profile,flags){
  const goal=salaryGoals(profile),pay=payEvidence(record);
  if(!goal.valid)return unknown('Set both a pay target and minimum in Search preferences to assess salary fit.');
  if(!pay)return unknown('Guaranteed base pay is not established. Estimates, total earnings and commissions cannot establish that your minimum is met.');
  const score=x=>x<goal.minimum?69*x/goal.minimum:goal.target===goal.minimum?100:70+30*(x-goal.minimum)/(goal.target-goal.minimum);
  let low=clamp(score(pay.low)),high=clamp(score(pay.high));
  if(pay.estimated){low=clamp(low-15);high=clamp(high+15);flags.push({text:'Pay is estimated or annualized; confirm the actual base.',cap:null});}
  if(pay.high<goal.minimum){flags.push({text:pay.estimated?'Estimated pay is below your minimum; employer pay needs confirmation.':'Published base range is below your minimum.',cap:pay.estimated?null:49});}
  else if(pay.low<goal.minimum)flags.push({text:'Pay range crosses your minimum; a qualifying offer is not guaranteed.',cap:null});
  return band(Math.round(low),Math.round(high),`Compared with target $${goal.target.toLocaleString('en-US')} and minimum $${goal.minimum.toLocaleString('en-US')}. ${pay.hourly?'Hourly pay assumes 2,080 paid hours per year. ':''}The lower and upper pay amounts produce the match range.`,pay.estimated?'estimated':'published range',[pay.text]);
}
function advancementScore(record,profile){
  const goals=interests(profile),f=family(record),p=record.careerPath;
  if(!goals)return unknown('Save your desired roles and industries to assess career alignment.');
  if(!p)return unknown('A sourced career ladder has not yet been prepared for this opportunity.');
  const researchGoal=/research|trial|pharma|biotech|safety/.test(goals);
  let result;
  if(researchGoal&&f==='research')result=band(80,95,'The work builds trial, data or safety experience directly relevant to your industry goals. Advancement still depends on assignments and demonstrated delivery.');
  else if(researchGoal&&f==='regulatory')result=band(70,85,'Research compliance can lead to study start-up or regulatory operations; it provides less end-to-end trial delivery.');
  else if(researchGoal&&f==='education')result=band(65,85,'Clinical education can build industry/client program experience. Moving into trial operations requires a research bridge.');
  else if(researchGoal&&f==='device')result=band(60,80,'A credible device-industry path, strongest for clinical support and education leadership. Drug-trial experience is an additional transition.');
  else if(researchGoal&&f==='commercial')result=band(40,65,'The clearest advancement is commercial leadership. Moving into clinical trials or drug development requires additional experience.');
  else if(researchGoal&&f==='healthcare')result=band(30,55,'Healthcare quality/review work is an indirect industry bridge; seek actual research or regulated-development assignments.');
  else if(f==='healthcare'&&/review|quality|documentation|informatics|utilization/.test(goals))result=band(65,85,'This aligns with a saved healthcare career direction; review the ladder for the specific next role.');
  else return unknown('The available career ladder has not been assessed against your current career direction.');
  if(f==='research'&&(p.gaps||[]).some(x=>/mainly laboratory|confirm whether.*interventional/i.test(x)))result=band(55,85,'The role’s interventional trial scope is not established. Confirm whether you would own study operations or mainly laboratory/sample support.');
  result.evidence=[p.industryBridge,p.summary];return result;
}
function interestScore(record,profile){
  const rating=record.interestRating;
  if(rating&&Number.isFinite(rating.value))return band(rating.value,rating.value,'Your own saved interest rating. It expresses preference, not qualification.','your rating',rating.note?[rating.note]:[]);
  const goals=interests(profile),f=family(record);
  if(!goals)return unknown('You have not rated your interest or saved target role families.');
  let aligned=f==='research'&&/research|trial|pharma|biotech|safety/.test(goals)||f==='regulatory'&&/research|trial/.test(goals)||f==='healthcare'&&/quality|review|documentation|informatics|utilization/.test(goals)||f==='education'&&/educat|pharma|biotech/.test(goals)||f==='device'&&/device|specialist/.test(goals)||f==='commercial'&&/sales|commercial/.test(goals);
  return band(aligned?70:35,aligned?90:65,'Goal-alignment estimate from your saved role families. Your personal interest is not rated yet; set it below to replace this estimate.','goal alignment',[`Saved search roles: ${(profile.searchPreferences?.roles||[]).join(', ')}`]);
}
function backgroundScore(record,profile,flags){
  const all=profile.entries||[],confirmed=all.filter(e=>e.confirmed&&e.category!=='Preference'),candidates=all.filter(e=>e.category!=='Preference');
  const text=candidates.map(e=>e.text).join(' ').toLowerCase();
  if(!text)return unknown('No reviewed background or source-based Career memory is available to compare.');
  const nursing=/\bnurs|\brn\b|\bbsn\b/.test(text),clinical=/clinical|nurs|patient/i.test(record.posting+' '+record.title);
  const evidence=[];
  const requirements=(record.requirements||[]).filter(r=>r.kind==='Requirement');
  const supported=requirements.filter(r=>r.reviewed&&r.evidenceId?.startsWith('fact:')&&confirmed.some(e=>e.id===r.evidenceId.slice(5)));
  if(supported.length)evidence.push(`${supported.length} of ${requirements.length} extracted required passages have reviewed links to confirmed facts; links are your assessment, not independent credential checks.`);
  const posting=record.posting.toLowerCase(),verifiedText=confirmed.map(e=>e.text).join(' ').toLowerCase();
  const gaps=[];
  if(/advanced.*cardiac pacing|advanced pacing/.test(posting)&&!/pacing|pacemaker/.test(verifiedText))gaps.push('Advanced cardiac pacing experience needs evidence.');
  if(/peripheral.*procedure.*required/.test(posting)&&!/peripheral.*procedure|cath lab/.test(verifiedText))gaps.push('Required peripheral procedure experience needs evidence.');
  if(/oncology research.*required|two.plus.*oncology research|two.*years.*oncology research/.test(posting)&&!/oncology research/.test(verifiedText))gaps.push('Required oncology research experience needs evidence.');
  if(/phase.*trial experience|experience.*phases? i.?iv|experience.*phases? 1.?4/.test(posting)&&!/clinical trial|clinical research/.test(verifiedText))gaps.push('Required trial-phase experience needs evidence.');
  if(/people leadership.*direct reports|direct.report.*leadership.*required|three.plus years.*people/.test(posting)&&!/direct reports|performance management/.test(verifiedText))gaps.push('Required direct-report management is not established by charge/precepting alone.');
  if(/sales experience required|sales.*experience required/.test(posting)&&!/sales|territory management/.test(verifiedText))gaps.push('Required sales experience needs evidence.');
  if(/cath lab.*scrubbing|cath lab.*including scrubbing/.test(posting)&&!/cath lab|scrubbing/.test(verifiedText))gaps.push('Cath lab/scrubbing experience needs evidence.');
  if(/requires two years clinical research|requires.*clinical research and.*clinical safety/.test(posting)&&!/clinical research|clinical safety/.test(verifiedText))gaps.push('Required research and safety operations experience needs evidence.');
  if(gaps.length){flags.push(...gaps.map(text=>({text,cap:null})));return band(25,55,'Transferable clinical skills do not establish the specific required experience. These gaps are unconfirmed, not proof you lack the skill.','provisional',gaps.concat(evidence));}
  if(!nursing||!clinical)return unknown('The available background has not been matched to this role’s actual requirements.');
  if(record.careerPath?.entryFit)evidence.push(record.careerPath.entryFit);
  if(!confirmed.length)return band(55,75,'Source-based nursing, clinical judgment and education experience may transfer. Career memory facts remain unconfirmed; specialty requirements still need review.','provisional',evidence);
  if(requirements.length&&supported.length===requirements.length)return band(85,95,'All extracted required passages have reviewed links to confirmed facts. The posting may contain other requirements not extracted.','reviewed evidence',evidence);
  return band(60,80,'Confirmed clinical background supports transferable skills; full requirement coverage and specialty experience are not established.','partial evidence',evidence);
}
function practicalScore(record,profile,flags){
  if(!profile.searchPreferences?.constraints?.trim()&&!profile.searchPreferences?.location?.trim()&&!profile.searchPreferences?.remote)return unknown('Save practical preferences to assess travel, location and work arrangement.');
  const raw=[record.schedule,record.posting,...(record.concerns||[])].filter(Boolean).join(' ');
  const outsideBedside=/outside bedside|leave bedside|non.bedside/i.test((profile.searchPreferences?.constraints||'')+' '+(profile.researchFeedback||[]).filter(r=>r.status==='active'&&r.sourceType==='user').map(r=>r.text).join(' '));
  if(outsideBedside&&!/educat|specialist|coordinat|review|research|manager|supervisor/i.test(record.title)&&/staff (?:rn|nurse|registered nurse)|bedside|registered nurse.*(?:icu|intensive care)|(?:icu|intensive care).*registered nurse/i.test(record.title)){flags.push({text:'This is a bedside staff role, conflicting with your goal to leave bedside.',cap:49});return band(0,20,'The role title describes bedside staff nursing, which conflicts with active non-bedside guidance.','stated conflict',[record.title]);}
  const minimal=/minimal travel|limited travel|low travel|no travel(?:[.,;]|$)/i.test(profile.searchPreferences?.constraints||'');
  const percentages=[...raw.matchAll(/(?:travel[^.%]{0,35}?(\d{1,3})(?:\s*[–-]\s*(\d{1,3}))?\s*%|\b(\d{1,3})(?:\s*[–-]\s*(\d{1,3}))?\s*%\s*(?:regional\s+|national\s+|local\s+)?travel)/gi)].map(m=>Math.max(...m.slice(1).filter(Boolean).map(Number))).filter(n=>n<=100);
  const travel=percentages.length?Math.max(...percentages):null;
  if(minimal&&(travel>=50||/three to four overnight|3.?4 overnight|road warrior|most weeks/.test(raw.toLowerCase()))){flags.push({text:'Heavy travel conflicts with your minimal-travel preference.',cap:49});return band(0,25,'At least 50% travel or frequent overnight work is stated. This conflicts with your saved minimal-travel constraint.','stated conflict',[record.schedule||`${travel}% travel mentioned in saved role evidence.`]);}
  let result;
  if(minimal&&travel!==null&&travel>10){flags.push({text:'Travel is a tradeoff to clarify against your minimal-travel preference.',cap:null});result=band(30,60,'Regional travel above 10% is stated; your preference does not establish an exact numerical limit. Confirm overnight frequency and territory.');}
  else if(minimal&&travel!==null)result=band(65,85,'Listed travel is 10% or less. Confirm overnights, call and whether this is acceptable to you.');
  else if(minimal&&/field.based|field territory|overnight|travel.*(?:undisclosed|not disclosed|not specified)/i.test(raw))result=band(20,70,'The role involves field coverage or overnight travel without enough detail to establish a fit.');
  else if(/office.based|onsite|on.site|remote|day shift|monday/i.test(raw))result=band(55,85,'The saved work arrangement could fit, but travel, commute, residency and schedule are not all verified.');
  else result=unknown('Travel, location and schedule have not been established against your preferences.');
  if(/relocation required|must live commutable|ohio eligibility unconfirmed|ohio eligibility.*not confirmed/i.test(raw)){flags.push({text:'Location or relocation requirements need confirmation.',cap:null});result.low=0;result.high=Math.min(result.high,60);}
  const p=record.careerPath;if(p?.bedsideFit){result.evidence.push(p.bedsideFit);if(/patient visits|participant care|patient care|procedural|procedures/i.test(p.bedsideFit))flags.push({text:'Outside inpatient bedside may still involve patient-facing or procedural work.',cap:null});}
  if(profile.searchPreferences?.remote==='only'&&!/\bremote\b/i.test((record.schedule||'')+' '+(record.location||''))){result.low=0;result.high=Math.min(result.high,50);flags.push({text:'Remote-only preference is not established for this role.',cap:null});}
  result.evidence.push(`Saved location: ${profile.searchPreferences?.location||'No explicit location filter'}. Constraints: ${profile.searchPreferences?.constraints||'None recorded'}.`);
  return result;
}
function assess(record,profile){
  const flags=[];
  const components={pay:payScore(record,profile,flags),advancement:advancementScore(record,profile),interest:interestScore(record,profile),background:backgroundScore(record,profile,flags),practical:practicalScore(record,profile,flags)};
  const weights={...DEFAULT_WEIGHTS,...profile.matchPreferences?.weights};
  const total=Object.values(weights).reduce((a,b)=>a+b,0)||1;
  let low=0,high=0;
  for(const [key,c] of Object.entries(components)){c.label=LABELS[key];c.weight=Math.round(weights[key]/total*100);low+=c.low*weights[key]/total;high+=c.high*weights[key]/total;}
  if(record.interestRating?.value===0&&weights.interest>0)flags.push({text:'You marked this role Not interested.',cap:49});
  const cap=Math.min(100,...flags.filter(x=>x.cap!==null).map(x=>x.cap));
  low=Math.floor(Math.min(low,cap));high=Math.ceil(Math.min(high,cap));
  return {low,high,components,flags,cap,weights,assessed:Object.entries(components).filter(([k,c])=>weights[k]>0&&c.status!=='unknown').length,totalFactors:Object.values(weights).filter(x=>x>0).length,sourceDate:record.verifiedAt||record.careerPath?.updatedAt||'',goals:salaryGoals(profile)};
}
const api={assess,salaryGoals,payEvidence,DEFAULT_WEIGHTS,LABELS};root.CareerMatch=api;
if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
