// Browser acceptance for the static nutrition-site demo.
// Run: npm install --no-save playwright-core && node scripts/smoke.mjs
import { chromium, webkit } from 'playwright-core';
import { resolve, extname, sep } from 'node:path';
import { createServer } from 'node:http';
import { createReadStream } from 'node:fs';
import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import assert from 'node:assert/strict';

const engine=process.env.BROWSER_ENGINE==='webkit'?'webkit':'chromium';
const binary = process.env.CHROME_BIN || ['/usr/bin/google-chrome','/usr/bin/chromium','/usr/bin/chromium-browser'].find(existsSync);
if (engine==='chromium'&&!binary) throw Error('Chromium binary not available');
const browser=engine==='webkit'
  ? await webkit.launch({headless:true})
  : await chromium.launch({executablePath:binary,headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
// Serve the built site over HTTP so resource timing is measured correctly.
const root=resolve('_site');
const mime={'.html':'text/html; charset=utf-8','.webp':'image/webp','.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png','.css':'text/css','.js':'text/javascript','.svg':'image/svg+xml'};
const server=createServer((req,res)=>{
  let pathname;
  try { pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname); }
  catch { res.writeHead(400).end(); return; }
  const target=resolve(root,'.'+pathname);
  if(target!==root&&!target.startsWith(root+sep)){res.writeHead(403).end();return;}
  const file=target===root?resolve(root,'index.html'):target;
  if(!existsSync(file)){res.writeHead(404).end();return;}
  res.setHeader('Content-Type',mime[extname(file).toLowerCase()]||'application/octet-stream');
  res.setHeader('Cache-Control','public, max-age=3600');
  createReadStream(file).on('error',()=>{if(!res.headersSent)res.writeHead(500);res.end();}).pipe(res);
});
await new Promise((ok,fail)=>{server.once('error',fail);server.listen(0,'127.0.0.1',ok);});
const source='http://127.0.0.1:'+server.address().port+'/index.html';
const sizes=[
  {name:'small-mobile',width:360,height:780},
  {name:'mobile',width:390,height:844},
  {name:'tablet-portrait',width:768,height:1024},
  {name:'ipad',width:820,height:1180},
  {name:'tablet-landscape',width:1024,height:768},
  {name:'desktop',width:1440,height:900}
];
const selectedSizes=process.env.SMOKE_VIEWPORTS?.split(',').filter(Boolean);
const viewports=selectedSizes?.length?sizes.filter(s=>selectedSizes.includes(s.name)):sizes;
if(!viewports.length)throw Error('No viewports selected for '+engine);
const reports=[];
mkdirSync('screenshots',{recursive:true});
try {
  for(const size of viewports){
    const page=await browser.newPage({viewport:{width:size.width,height:size.height},deviceScaleFactor:2});
    const failures=[];
    await page.addInitScript(() => {
      window.__siteVitals={lcp:0,cls:0};
      try { new PerformanceObserver(list=>{for(const entry of list.getEntries()) window.__siteVitals.lcp=entry.startTime;}).observe({type:'largest-contentful-paint',buffered:true}); } catch {}
      try { new PerformanceObserver(list=>{for(const e of list.getEntries()) if(!e.hadRecentInput) window.__siteVitals.cls+=e.value;}).observe({type:'layout-shift',buffered:true}); } catch {}
    });
    page.on('pageerror',e=>failures.push('JS '+e.message));
    await page.goto(source+'#app',{waitUntil:'load'});
    await page.locator('#v45-meals .v45-meal').first().waitFor();
    const tabs=page.locator('[data-v45-day]');
    assert.equal(await tabs.count(),7,'exactly seven tabs');
    assert.equal(await page.locator('#v45-meals .v45-meal').count(),4,'four meals');
    const allWeekPhotoUrls=[];
    for(let day=0;day<7;day++){
      await tabs.nth(day).click();
      assert.equal(await tabs.nth(day).getAttribute('aria-pressed'),'true');
      assert.match(await page.locator('#v45-weekday').innerText(),/ПРИМЕР МЕНЮ/);
      const labels=await page.locator('#v45-meals [data-v45-name]').allTextContents();
      assert.equal(labels.length,4);
      assert.ok(labels.every(label=>label.trim().length>5));
      await page.waitForFunction(() => [...document.querySelectorAll('#v45-meals [data-v48-fullphoto]:not([hidden])')].every(img=>img.complete&&img.naturalWidth>=1200&&img.naturalHeight>=675),null,{timeout:5000});
      const fidelity=await page.locator('#v45-meals [data-v45-photo]').evaluateAll(nodes=>nodes.map(node=>{
        const active=node.querySelector('[data-v48-fullphoto]:not([hidden])');
        const classPhoto=[...node.classList].find(name=>name.startsWith('v45-photo-'));
        return {classPhoto,activeSrc:active?.getAttribute('src')||null,
          imageComplete:!!active&&(active.complete&&active.naturalWidth>=1200&&active.naturalHeight>=675)};
      }));
      for(const item of fidelity){
        if(item.classPhoto==='v45-photo-steak')assert.ok((item.activeSrc||'').endsWith('/hero-02-steak.webp'),'approved steak photo path');
        if(item.classPhoto==='v45-photo-salmon')assert.ok((item.activeSrc||'').endsWith('/hero-01-fish.webp'),'approved salmon photo path');
        assert.ok(item.activeSrc, 'every meal requires its own image mapping on day '+day);
        assert.ok(item.imageComplete, 'active Retina-resolution food photo must load on day '+day);
        allWeekPhotoUrls.push(item.activeSrc);
      }
    }
    assert.equal(allWeekPhotoUrls.length,28,'all menu photos checked');
    assert.equal(new Set(allWeekPhotoUrls).size,28,'all 28 meals must use separate actual image URLs');
    await tabs.first().focus();
    await page.keyboard.press('ArrowRight');
    assert.equal(await tabs.nth(1).getAttribute('aria-pressed'),'true','keyboard next day');
    await page.keyboard.press('End');
    assert.equal(await tabs.nth(6).getAttribute('aria-pressed'),'true','keyboard last day');
    await tabs.first().click();
    const photos=await page.locator('#v45-meals [data-v45-photo]').evaluateAll(nodes=>nodes.map(node=>{
      const image=node.querySelector('img:not([hidden])');
      return {width:node.getBoundingClientRect().width,height:node.getBoundingClientRect().height,
        image:image?{complete:image.complete,naturalWidth:image.naturalWidth,src:image.getAttribute('src')}:null,
        background:getComputedStyle(node).backgroundImage};
    }));
    for(const p of photos){
      assert.ok(p.width>150&&p.height>80,'photo region size');
      if(p.image)assert.ok(p.image.complete&&p.image.naturalWidth>=1200,'high-res meal photo must load');
      else assert.fail('A meal photo must never fall back to the old atlas');
    }
    const metrics=await page.evaluate(()=>({
      scrollWidth:document.documentElement.scrollWidth,
      innerWidth:window.innerWidth,
      broken:[...document.querySelectorAll('img[src]')].filter(img=>img.complete&&img.naturalWidth===0).map(img=>img.src)
    }));
    assert.ok(metrics.scrollWidth <= metrics.innerWidth+2,
      size.name+' horizontal overflow '+JSON.stringify(metrics));
    assert.deepEqual(metrics.broken,[],'all regular images load');
    assert.deepEqual(failures,[],'JavaScript console errors');
    const performance=await page.evaluate(()=>{
      const nav=performance.getEntriesByType('navigation')[0];
      const paint=performance.getEntriesByType('paint');
      const resources=performance.getEntriesByType('resource').filter(r=>/\.(webp|png|jpg|jpeg)(\?|$)/i.test(r.name));
      const uniqueUrls=[...new Set(resources.map(r=>r.name))];
      const largest=resources.slice().sort((a,b)=>b.duration-a.duration).slice(0,5).map(r=>({
        url:r.name.split('/').slice(-2).join('/'),
        durationMs:Math.round(r.duration),
        transferBytes:r.transferSize||0
      }));
      return {
        navigationMs:Math.round(nav?.duration||0),
        domContentLoadedMs:Math.round(nav?.domContentLoadedEventEnd||0),
        firstContentfulPaintMs:Math.round(paint.find(p=>p.name==='first-contentful-paint')?.startTime||0),
        largestContentfulPaintMs:Math.round(window.__siteVitals?.lcp||0),
        layoutShift:Number((window.__siteVitals?.cls||0).toFixed(4)),
        imageRequests:resources.length,
        distinctImageUrls:uniqueUrls.length,
        slowestImageRequests:largest
      };
    });
    reports.push({viewport:size.name,width:size.width,height:size.height,...performance});
    await page.locator('#app').screenshot({path:'screenshots/qa-app-'+engine+'-'+size.name+'.png',animations:'disabled'});
    console.log('PASS',engine,size.name, '7 day clicks, keyboard, images, layout, JS');
    await page.close();
  }
}finally{
  writeFileSync('screenshots/performance-report-'+engine+'.json',JSON.stringify({kind:engine+' laboratory diagnostics; not physical iPad Safari or field Core Web Vitals',results:reports},null,2));
  await browser.close();
  await new Promise(ok=>server.close(ok));
}
