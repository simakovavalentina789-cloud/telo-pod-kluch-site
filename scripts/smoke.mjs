// Browser acceptance for the static nutrition-site demo.
// Run: npm install --no-save playwright-core && node scripts/smoke.mjs
import { chromium } from 'playwright-core';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { existsSync, mkdirSync } from 'node:fs';
import assert from 'node:assert/strict';

const binary = process.env.CHROME_BIN || ['/usr/bin/google-chrome','/usr/bin/chromium','/usr/bin/chromium-browser'].find(existsSync);
if (!binary) throw Error('Chromium binary not available');
const browser=await chromium.launch({executablePath:binary,headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
const source=pathToFileURL(resolve('_site/index.html')).href;
const sizes=[{name:'mobile',width:390,height:844},{name:'ipad',width:820,height:1180},{name:'desktop',width:1440,height:900}];
mkdirSync('screenshots',{recursive:true});
try {
  for(const size of sizes){
    const page=await browser.newPage({viewport:{width:size.width,height:size.height},deviceScaleFactor:2});
    const failures=[];
    page.on('pageerror',e=>failures.push('JS '+e.message));
    await page.goto(source+'#app',{waitUntil:'load'});
    await page.locator('#v45-meals .v45-meal').first().waitFor();
    const tabs=page.locator('[data-v45-day]');
    assert.equal(await tabs.count(),7,'exactly seven tabs');
    assert.equal(await page.locator('#v45-meals .v45-meal').count(),4,'four meals');
    for(let day=0;day<7;day++){
      await tabs.nth(day).click();
      assert.equal(await tabs.nth(day).getAttribute('aria-pressed'),'true');
      assert.match(await page.locator('#v45-weekday').innerText(),/ПРИМЕР МЕНЮ/);
      const labels=await page.locator('#v45-meals [data-v45-name]').allTextContents();
      assert.equal(labels.length,4);
      assert.ok(labels.every(label=>label.trim().length>5));
      await page.waitForFunction(() => [...document.querySelectorAll('#v45-meals [data-v48-fullphoto]:not([hidden])')].every(img=>img.complete&&img.naturalWidth>=800),{timeout:5000});
      const fidelity=await page.locator('#v45-meals [data-v45-photo]').evaluateAll(nodes=>nodes.map(node=>{
        const active=node.querySelector('[data-v48-fullphoto]:not([hidden])');
        const classPhoto=[...node.classList].find(name=>name.startsWith('v45-photo-'));
        return {classPhoto,activeSrc:active?.getAttribute('src')||null,
          imageComplete:!active||(active.complete&&active.naturalWidth>=800)};
      }));
      for(const item of fidelity){
        if(item.classPhoto==='v45-photo-steak')assert.match(item.activeSrc||'',/hero-02-steak\\.webp$/);
        if(item.classPhoto==='v45-photo-salmon')assert.match(item.activeSrc||'',/hero-01-fish\\.webp$/);
        assert.ok(item.imageComplete, 'active full-res dish must load in day '+day);
      }
    }
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
      if(p.image)assert.ok(p.image.complete&&p.image.naturalWidth>=800,'high-res meal photo must load');
      else assert.match(p.background,/v45-food-atlas.webp/,'fallback atlas must load');
    }
    const metrics=await page.evaluate(()=>({
      scrollWidth:document.documentElement.scrollWidth,
      innerWidth:window.innerWidth,
      broken:[...document.querySelectorAll('img')].filter(img=>img.complete&&img.naturalWidth===0).map(img=>img.src)
    }));
    assert.ok(metrics.scrollWidth <= metrics.innerWidth+2,
      size.name+' horizontal overflow '+JSON.stringify(metrics));
    assert.deepEqual(metrics.broken,[],'all regular images load');
    assert.deepEqual(failures,[],'JavaScript console errors');
    await page.locator('#app').screenshot({path:'screenshots/qa-app-'+size.name+'.png',animations:'disabled'});
    console.log('PASS',size.name, '7 day clicks, keyboard, images, layout, JS');
    await page.close();
  }
}finally{await browser.close();}
