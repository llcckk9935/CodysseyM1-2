'use strict';
const $ = id => document.getElementById(id);
const base = (window.APP_CONFIG?.API_BASE_URL || '').replace(/\/$/,'');
const state = {rows:[],summary:null,page:0,conversation:null,editing:null,busy:false};
let session;
try { session=localStorage.getItem('fuel-session'); if(!session){session=crypto.randomUUID()+crypto.randomUUID();localStorage.setItem('fuel-session',session);} }
catch { session=crypto.randomUUID()+crypto.randomUUID(); }
const fmt = n => Number(n).toLocaleString('ko-KR',{minimumFractionDigits:2,maximumFractionDigits:2});
function status(id,message,error=false){$(id).textContent=message;$(id).classList.toggle('error',error);}
async function api(path,options={}){
  const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),60000);
  try {
    const response=await fetch(base+path,{...options,signal:controller.signal,headers:{'Content-Type':'application/json','X-Session-Token':session,...options.headers}});
    if(response.status===204)return null;
    const body=await response.json();
    if(!response.ok)throw new Error(typeof body.detail==='string'?body.detail:`요청 실패 (${response.status}). 입력값과 연결 상태를 확인하세요.`);
    return body;
  } catch(e){if(e.name==='AbortError')throw new Error('서버 응답을 기다리는 시간이 초과됐습니다. 잠시 후 다시 시도하세요.');throw e;}
  finally{clearTimeout(timeout);}
}
function element(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;}
function renderSummary(s){
  state.summary=s;$('average').textContent=s.metrics?fmt(s.metrics.average):'—';
  $('minimum').textContent=s.metrics?fmt(s.metrics.min):'—';$('maximum').textContent=s.metrics?fmt(s.metrics.max):'—';
  $('min-date').textContent=s.metrics?s.metrics.min_dates.join(', '):'—';$('max-date').textContent=s.metrics?s.metrics.max_dates.join(', '):'—';
  $('trend').textContent=s.trend.status;$('trend-detail').textContent=s.trend.difference===undefined?'14일 연속 기록이 필요합니다.':`${s.trend.difference>0?'+':''}${fmt(s.trend.difference)}원/리터 (${s.trend.change_pct}%)`;
  $('period').textContent=s.period?`${s.period[0]} ~ ${s.period[1]} · ${s.count}개 기록 · 마지막 기준일 ${s.as_of}`:'저장된 데이터가 없습니다.';
  $('period-change').textContent=`기간 변화율: ${s.period_change_pct===null?'자료 부족':s.period_change_pct+'%'}`;
  const monthly=$('monthly');monthly.replaceChildren();
  if(s.monthly.length){const table=element('table');const head=element('tr');for(const text of ['월','기록 수','일별 단순평균 (원/리터)'])head.append(element('th',text));table.append(head);for(const m of s.monthly){const tr=element('tr');for(const text of [m.month,m.count,fmt(m.average)])tr.append(element('td',text));table.append(tr);}monthly.append(table);}
  status('notice',`${s.count}개 기록을 불러왔습니다.${s.modified_count||s.user_input_count?` 수정 ${s.modified_count||0}개 · 사용자 추가 ${s.user_input_count||0}개가 포함되어 있습니다.`:''} 실시간 가격이 아닌 저장 기록입니다.`);
}
function renderChart(){
  const box=$('chart');box.replaceChildren();const rows=state.rows;
  if(!rows.length){box.append(element('p','표시할 가격 기록이 없습니다.','empty'));return;}
  const ns='http://www.w3.org/2000/svg';const svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 1000 280');
  const make=(tag,attrs,text)=>{const e=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);if(text)e.textContent=text;svg.append(e);return e;};
  const values=rows.map(r=>Number(r.value));const lo=Math.min(...values),hi=Math.max(...values);const pad=Math.max((hi-lo)*.12,1);const min=lo-pad,max=hi+pad;
  const day=d=>Date.parse(d+'T00:00:00Z');const first=day(rows[0].date),last=day(rows.at(-1).date);const x=r=>70+(last===first?.5:(day(r.date)-first)/(last-first))*900;const y=v=>235-(v-min)/(max-min)*210;
  for(let i=0;i<5;i++){const v=min+(max-min)*i/4;make('line',{x1:70,y1:y(v),x2:970,y2:y(v),class:'grid'});make('text',{x:60,y:y(v)+4,'text-anchor':'end'},fmt(v));}
  const paths=[];let segment=[];for(const r of rows){if(segment.length&&day(r.date)-day(segment.at(-1).date)>86400000){paths.push(segment);segment=[];}segment.push(r);}if(segment.length)paths.push(segment);
  for(const seg of paths){const pts=seg.map(r=>`${x(r)},${y(r.value)}`).join(' ');make('polygon',{points:`${x(seg[0])},235 ${pts} ${x(seg.at(-1))},235`,class:'price-area'});make('polyline',{points:pts,class:'price-line'});for(const r of seg){const c=make('circle',{cx:x(r),cy:y(r.value),r:rows.length===1?4:2,fill:'var(--accent)'});const title=document.createElementNS(ns,'title');title.textContent=`${r.date}: ${fmt(r.value)}원/리터`;c.append(title);}}
  make('text',{x:70,y:265},rows[0].date);make('text',{x:970,y:265,'text-anchor':'end'},rows.at(-1).date);box.append(svg);box.setAttribute('aria-label',`${rows[0].date}부터 ${rows.at(-1).date}까지 ${rows.length}개 가격 기록. 최저 ${fmt(lo)}, 최고 ${fmt(hi)}원/리터.`);
}
function cancelEdit(){state.editing=null;$('data-form').reset();$('date').disabled=false;$('save-data').textContent='기록 추가';$('cancel-edit').hidden=true;}
function renderRows(){
  const maxPage=Math.max(0,Math.ceil(state.rows.length/15)-1);state.page=Math.min(state.page,maxPage);
  const body=$('data-rows');body.replaceChildren();const slice=state.rows.slice().reverse().slice(state.page*15,(state.page+1)*15);
  for(const r of slice){const tr=element('tr');tr.append(element('td',r.date),element('td',fmt(r.value)));const source=element('td');source.append(element('span',r.is_modified?'원본 가격 수정':r.source==='user'?'사용자 추가':'가져온 원본','badge'));tr.append(source,element('td',r.memo||'—'));const actions=element('td');
    const edit=element('button','수정','secondary');edit.disabled=state.busy;edit.onclick=()=>{state.editing=r.id;$('date').value=r.date;$('date').disabled=true;$('value').value=r.value;$('memo').value=r.memo||'';$('save-data').textContent='수정 저장';$('cancel-edit').hidden=false;$('value').focus();};
    const del=element('button','삭제','secondary');del.disabled=state.busy;del.onclick=async()=>{if(!confirm(`${r.date} 기록을 삭제하시겠습니까?`))return;const token=$('admin-token').value;if(!token){status('data-status','편집 인증 토큰을 입력하세요.',true);return;}setBusy(true);try{await api('/api/data/'+encodeURIComponent(r.id),{method:'DELETE',headers:{'X-Admin-Token':token}});if(state.editing===r.id)cancelEdit();status('data-status','기록을 삭제했습니다.');await loadData();}catch(e){status('data-status',e.message,true);}finally{setBusy(false);}};
    actions.append(edit,del);tr.append(actions);body.append(tr);}
  if(!slice.length){const tr=element('tr');const td=element('td','저장된 기록이 없습니다.');td.colSpan=5;tr.append(td);body.append(tr);}
  $('page-label').textContent=`${state.page+1} / ${maxPage+1} 페이지`;$('prev').disabled=state.page===0;$('next').disabled=state.page>=maxPage;
}
function setBusy(b){state.busy=b;for(const id of ['send','new-chat','save-data','cancel-edit','refresh-data','refresh-history','question'])$(id).disabled=b;document.querySelectorAll('[data-question], #history button').forEach(e=>e.disabled=b);renderRows();}
async function loadData(){
  try{const [rows,s]=await Promise.all([api('/api/data'),api('/api/data/summary')]);state.rows=rows;renderSummary(s);renderRows();renderChart();$('export').disabled=!rows.length;}
  catch(e){status('notice','데이터를 불러오지 못했습니다: '+e.message,true);}
}
function addMessage(role,text){const messages=$('messages');messages.querySelector('.empty')?.remove();const m=element('div',undefined,'message '+role);m.append(element('small',role==='user'?'나':'분석 비서'),document.createTextNode(text));messages.append(m);messages.scrollTop=messages.scrollHeight;}
function showTools(trace){
  if(!trace.length)return;
  const details=element('details');details.append(element('summary','사용한 도구와 조회 근거'));
  for(const item of trace){const label=item.name==='get_data_summary'?'가격 요약 조회':item.name==='get_conversation_history'?'현재 대화 조회':item.name;details.append(element('p',`${label} · ${item.status==='success'?'성공':'오류'}${item.arguments?.reason?' · '+item.arguments.reason:''}${item.result_count!==undefined?' · '+item.result_count+'개 기록':''}`));}
  $('messages').append(details);
}
async function loadHistory(){
  const box=$('history');try{const rows=await api('/api/conversations');box.replaceChildren();if(!rows.length){box.append(element('p','저장된 대화가 없습니다.','empty'));return;}
    for(const r of rows){const item=element('div',undefined,'history-item');const open=element('button',r.title,'open');open.disabled=state.busy;open.append(element('small',`${r.message_count}개 메시지`));open.onclick=async()=>{setBusy(true);try{const c=await api('/api/conversations/'+r.id);state.conversation=c.id;$('messages').replaceChildren();for(const m of c.messages)addMessage(m.role,m.content);status('chat-status','이전 대화를 불러왔습니다. 당시 답변의 가격과 현재 데이터가 다를 수 있습니다.');}catch(e){status('chat-status',e.message,true);}finally{setBusy(false);}};
      const del=element('button','삭제','secondary delete');del.disabled=state.busy;del.setAttribute('aria-label',`${r.title} 대화 삭제`);del.onclick=async()=>{if(!confirm('이 대화를 삭제하시겠습니까?'))return;setBusy(true);try{await api('/api/conversations/'+r.id,{method:'DELETE'});if(state.conversation===r.id)newChat();await loadHistory();}catch(e){status('chat-status',e.message,true);}finally{setBusy(false);}};item.append(open,del);box.append(item);}
  }catch(e){box.replaceChildren(element('p','목록을 불러오지 못했습니다: '+e.message,'caption'));}
}
function newChat(){state.conversation=null;$('messages').replaceChildren(element('p','궁금한 가격 흐름을 물어보세요.','empty'));status('chat-status','');$('question').value='';}
$('chat-form').onsubmit=async e=>{e.preventDefault();if(state.busy)return;const question=$('question').value.trim();if(!question)return;setBusy(true);addMessage('user',question);status('chat-status','가격 요약을 확인하고 답변을 생성하는 중입니다…');try{const result=await api('/api/chat',{method:'POST',body:JSON.stringify({message:question,conversation_id:state.conversation})});addMessage('assistant',result.answer);showTools(result.tool_trace||[]);if(result.saved){state.conversation=result.conversation_id;$('question').value='';status('chat-status','답변과 대화를 저장했습니다.');await loadHistory();}else{status('chat-status',result.warning,true);} }catch(err){status('chat-status',err.message+' 질문은 입력창에 남겨두었습니다.',true);}finally{setBusy(false);}};
$('data-form').onsubmit=async e=>{e.preventDefault();if(state.busy)return;const token=$('admin-token').value;if(!token){status('data-status','편집 인증 토큰을 입력하세요.',true);return;}const body={date:$('date').value,value:Number($('value').value),memo:$('memo').value};setBusy(true);try{await api('/api/data'+(state.editing?'/'+state.editing:''),{method:state.editing?'PUT':'POST',headers:{'X-Admin-Token':token},body:JSON.stringify(body)});cancelEdit();status('data-status','기록을 저장했습니다.');await loadData();}catch(err){status('data-status',err.message,true);}finally{setBusy(false);}};
$('cancel-edit').onclick=cancelEdit;$('new-chat').onclick=newChat;$('refresh-data').onclick=loadData;$('refresh-history').onclick=loadHistory;
$('prev').onclick=()=>{state.page--;renderRows();};$('next').onclick=()=>{state.page++;renderRows();};
document.querySelectorAll('[data-question]').forEach(b=>b.onclick=()=>{$('question').value=b.dataset.question;$('question').focus();});
function applyTheme(dark){document.documentElement.dataset.theme=dark?'dark':'light';$('theme').setAttribute('aria-pressed',String(dark));$('theme').textContent=dark?'라이트 모드':'다크 모드';}
try{applyTheme(localStorage.getItem('fuel-theme')==='dark');}catch{applyTheme(false);}
$('theme').onclick=()=>{const dark=document.documentElement.dataset.theme!=='dark';applyTheme(dark);try{localStorage.setItem('fuel-theme',dark?'dark':'light');}catch{}};
$('export').onclick=()=>{
  const safe=value=>{let v=String(value??'');if(/^[\s]*[=+\-@\t\r]/.test(v))v="'"+v;return '"'+v.replace(/"/g,'""')+'"';};
  const lines=[['date','value','memo','source','is_modified','unit']];for(const r of state.rows)lines.push([r.date,r.value,r.memo,r.source,r.is_modified?'true':'false','KRW/L']);
  const blob=new Blob(['\ufeff'+lines.map(row=>row.map(safe).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'});const link=document.createElement('a');const url=URL.createObjectURL(blob);link.href=url;link.download='fuel-price-records.csv';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
loadData();loadHistory();
