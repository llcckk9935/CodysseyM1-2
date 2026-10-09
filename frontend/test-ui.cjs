// Browser checks use HTTP fixtures, not production services.
const {chromium}=require('playwright');
const fs=require('node:fs');
const assert=require('node:assert/strict');
(async()=>{
  const fixture=JSON.parse(fs.readFileSync(process.env.UI_FIXTURE,'utf8'));
  const browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const saved=[];
  await page.route('http://127.0.0.1:8000/**',async route=>{
    const req=route.request(),path=new URL(req.url()).pathname,method=req.method();
    const reply=(body,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(body),headers:{'Access-Control-Allow-Origin':'*'}});
    if(method==='OPTIONS')return route.fulfill({status:204,headers:{'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*','Access-Control-Allow-Methods':'*'}});
    if(path==='/api/data/summary')return reply(fixture.summary);
    if(path==='/api/data'&&method==='GET')return reply(fixture.rows);
    if(path==='/api/data'&&method==='POST'){
      const row=req.postDataJSON();fixture.rows.push({...row,id:row.date,source:'user',is_modified:false});return reply(row,201);
    }
    if(path.startsWith('/api/data/')&&method==='PUT'){
      const row=req.postDataJSON(),index=fixture.rows.findIndex(r=>r.id===path.split('/').at(-1));
      fixture.rows[index]={...fixture.rows[index],...row,is_modified:true};return reply(fixture.rows[index]);
    }
    if(path.startsWith('/api/data/')&&method==='DELETE'){
      fixture.rows=fixture.rows.filter(r=>r.id!==path.split('/').at(-1));return route.fulfill({status:204});
    }
    if(path==='/api/chat'){
      const payload=req.postDataJSON();const id='f7f3cdaa-3937-44b2-b5c9-3f380cb70bfb';
      saved.push({id,title:payload.message,message_count:2,messages:[{role:'user',content:payload.message},{role:'assistant',content:'테스트 응답: 저장 기간 평균 1680.32원/리터.'}]});
      return reply({answer:saved[0].messages[1].content,saved:true,conversation_id:id,summary:fixture.summary});
    }
    if(path==='/api/conversations')return reply(saved);
    if(path.startsWith('/api/conversations/')&&method==='GET')return reply(saved[0]);
    if(path.startsWith('/api/conversations/')&&method==='DELETE'){saved.length=0;return route.fulfill({status:204});}
    return reply({detail:'Unexpected fixture request'},404);
  });
  await page.goto('http://127.0.0.1:3000');
  await page.waitForFunction(()=>document.getElementById('average').textContent==='1,680.32');
  assert.equal(await page.locator('#chart svg').count(),1);
  await page.screenshot({path:process.env.UI_SCREENSHOT,fullPage:true});
  await page.locator('[data-question]').first().click();await page.locator('#send').click();
  await page.waitForFunction(()=>document.getElementById('chat-status').textContent.includes('저장했습니다'));
  await page.locator('#new-chat').click();await page.locator('#history .open').click();
  await page.waitForFunction(()=>document.getElementById('messages').textContent.includes('테스트 응답'));
  assert.equal(await page.locator('#history .open').isEnabled(),true);
  await page.locator('#theme').click();assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
  await page.reload();await page.waitForFunction(()=>document.getElementById('average').textContent==='1,680.32');
  assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');
  await page.locator('#theme').click();
  const download=page.waitForEvent('download');await page.locator('#export').click();
  const file=await download;const contents=fs.readFileSync(await file.path(),'utf8');
  assert(contents.includes('2025-01-01'));assert(contents.includes('KRW/L'));
  await page.locator('details').filter({has:page.locator('#admin-token')}).locator('summary').click();
  await page.locator('#admin-token').fill('fixture-token');
  await page.locator('#data-rows button').first().click();await page.locator('#value').fill('1800');await page.locator('#save-data').click();
  await page.waitForFunction(()=>document.getElementById('data-status').textContent==='기록을 저장했습니다.');
  assert((await page.locator('#data-rows').innerText()).includes('1,800.00'));
  await page.locator('#date').fill('2026-01-01');await page.locator('#value').fill('1700');await page.locator('#memo').fill('<img src=x onerror=alert(1)>');await page.locator('#save-data').click();
  await page.waitForFunction(()=>document.getElementById('data-rows').textContent.includes('2026-01-01'));
  assert.equal(await page.locator('#data-rows img').count(),0);
  page.on('dialog',d=>d.accept());await page.locator('#data-rows tr').first().locator('button').nth(1).click();
  await page.waitForFunction(()=>!document.getElementById('data-rows').textContent.includes('2026-01-01'));
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:process.env.UI_MOBILE_SCREENSHOT,fullPage:true});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
  assert.deepEqual(errors,[]);
  await browser.close();console.log('UI checks passed: summary, chart, chat, history, theme persistence, CSV, edit/add/delete, safe text, mobile layout.');
})().catch(e=>{console.error(e);process.exit(1);});
