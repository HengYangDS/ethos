import fs from "node:fs/promises";
import path from "node:path";
import { sha256 } from "../adapter/projection.mjs";
import { readEthosAtlasOutput } from "./atlas-output.mjs";
import { portablePath } from "architecture-publisher/source";

/** Lossless content packing. Reader locations are adapted only inside the frame.
 * @internal Focused verification seam; renderStandaloneAtlas owns the effect. */
export function composeStandaloneAtlas(selected) {
  if (!Array.isArray(selected.pages) || !selected.pages.length || selected.pages.length > 64)
    throw Error("Explicit complete atlas pages required");
  const members = new Map(selected.members.map((m) => [m.path, m.content]));
  const pages = {},
    blocks = [],
    shared = new Map();
  for (const page of selected.pages) {
    portablePath(page.path);
    const bytes = members.get(page.path);
    if (Object.hasOwn(pages, page.path) || !Buffer.isBuffer(bytes) || sha256(bytes) !== page.sha256)
      throw Error("Standalone page identity mismatch");
    const html = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    const pieces = [];
    let cursor = 0;
    const expression = /<(?:style|script)\b[^>]*>[\s\S]*?<\/(?:style|script)>/gi;
    for (const match of html.matchAll(expression)) {
      if (match.index > cursor) pieces.push(html.slice(cursor, match.index));
      if (!shared.has(match[0])) {
        shared.set(match[0], blocks.length);
        blocks.push(match[0]);
      }
      pieces.push(shared.get(match[0]));
      cursor = match.index + match[0].length;
    }
    pieces.push(html.slice(cursor));
    pages[page.path] = { pieces, sha256: page.sha256 };
  }
  if (!Object.hasOwn(pages, "index.html")) throw Error("Standalone overview page required");
  for (const page of selected.pages) {
    const html = members.get(page.path).toString("utf8");
    for (const m of html.matchAll(/<a\b[^>]*\bhref=["']([^"']+)["']/gi)) {
      const target = new URL(m[1], "https://atlas.invalid/" + page.path);
      if (
        target.origin === "https://atlas.invalid" &&
        target.pathname.endsWith(".html") &&
        !Object.hasOwn(pages, target.pathname.slice(1))
      )
        throw Error("Missing embedded page: " + target.pathname);
    }
    if (
      /<(?:script|iframe)\b[^>]*\bsrc\s*=/i.test(html) ||
      /<link\b[^>]*\bhref=["'](?:https?:|\/)/i.test(html)
    )
      throw Error("External executable or stylesheet is not embedded");
  }
  const licenses = {};
  for (const name of ["ARCHIFY-LICENSE.txt", "FONT-LICENSE.txt"]) {
    const bytes = members.get(name);
    if (!Buffer.isBuffer(bytes)) throw Error("Standalone license missing");
    licenses[name] = bytes.toString("utf8");
  }
  const data = JSON.stringify({ source: selected.source, pages, blocks, licenses }).replaceAll(
    "<",
    "\\u003c",
  );
  return `<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ETHOS · 问道 — Architecture</title><style>html,body{margin:0;width:100%;height:100%;background:#f5f3ed}#atlas{display:block;width:100%;height:100%;border:0}#error{padding:32px;font:16px/1.6 system-ui;color:#302e29}#error[hidden],#atlas[hidden]{display:none}</style></head><body><p id="error" hidden></p><noscript>This interactive atlas requires JavaScript. All pages and resources are contained in this file.</noscript><iframe id="atlas" title="ETHOS architecture atlas" allow="fullscreen; clipboard-write" allowfullscreen></iframe><script id="atlas-data" type="application/json">${data}</script><script>(${standaloneReader.toString()})();</script></body></html>\n`;
}

// prettier-ignore
function standaloneReader() {
  'use strict';
  const data=JSON.parse(document.getElementById('atlas-data').textContent);
  const frame=document.getElementById('atlas'),error=document.getElementById('error');
  let active=null;
  const hasPage=p=>Object.prototype.hasOwnProperty.call(data.pages,p);
  function select(){
    const url=new URL(location.href);
    if(url.hash.startsWith('#atlas=')){const state=new URLSearchParams(url.hash.slice(7));return{page:state.get('page')||'index.html',query:state.get('query')||'?theme=light',hash:state.get('hash')||''};}
    const page=url.searchParams.get('page')||'index.html';url.searchParams.delete('page');return{page,query:url.search||'?theme=light',hash:url.hash};
  }
  function virtualUrl(){const state=select(),url=new URL(location.href);url.search=state.query;url.searchParams.set('page',state.page);url.hash=state.hash;return url;}
  function writeState(state,replace){const url=new URL(location.href);url.hash='atlas='+new URLSearchParams(state).toString();try{history[replace?'replaceState':'pushState'](null,'',url);}catch(_){if(replace)location.replace(url.hash);else location.hash=url.hash;}}
  window.__atlasLocation={};
  for(const key of ['href','pathname','search','hash','origin'])Object.defineProperty(window.__atlasLocation,key,{get:()=>virtualUrl()[key]});
  window.__atlasHistory=function(url,replace){const target=new URL(url,virtualUrl());const page=target.searchParams.get('page')||select().page;target.searchParams.delete('page');writeState({page,query:target.search,hash:target.hash},replace);};
  function bridge(){
    const parentWindow=window.parent;
    window.__atlasLocation={};
    for(const key of ['href','pathname','search','hash','origin'])Object.defineProperty(window.__atlasLocation,key,{get:()=>parentWindow.__atlasLocation[key]});
    window.__atlasHistory={replaceState:function(state,title,url){parentWindow.__atlasHistory(url,true);},pushState:function(state,title,url){parentWindow.__atlasHistory(url,false);}};
    document.addEventListener('click',function(event){
      const anchor=event.target.closest&&event.target.closest('a[data-atlas-page]');if(!anchor)return;
      if(event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey){anchor.target='_top';return;}
      event.preventDefault();parentWindow.__atlasNavigate(anchor.dataset.atlasPage,anchor.dataset.atlasQuery,anchor.dataset.atlasHash);
    },true);
  }
  function hydrate(page){
    const html=data.pages[page].pieces.map(x=>typeof x==='number'?data.blocks[x]:x).join('');
    const doc=new DOMParser().parseFromString(html,'text/html');
    for(const anchor of doc.querySelectorAll('a[href]')){
      const target=new URL(anchor.getAttribute('href'),'https://atlas.invalid/'+page);
      if(target.origin!=='https://atlas.invalid'||!target.pathname.endsWith('.html'))continue;
      const name=target.pathname.slice(1);if(!hasPage(name))throw new Error('Missing embedded page: '+name);
      anchor.dataset.atlasPage=name;anchor.dataset.atlasQuery=target.search;anchor.dataset.atlasHash=target.hash;
      const link=new URL(location.href);link.hash='atlas='+new URLSearchParams({page:name,query:target.search,hash:target.hash}).toString();anchor.href=link.href;anchor.target='_top';
    }
    for(const script of doc.scripts){
      if(script.type&&!['text/javascript','application/javascript'].includes(script.type))continue;
      if(script.src)throw new Error('External script is not embedded');
      // Location adaptation must not hide the native public runtime in a closure.
      // Internal methods and external consumers share this one native object.
      const source=script.textContent.replace('var Archify = {};','var Archify = window.Archify = {};');
      script.textContent='(function(location,history){\n'+source.replace(/window\.location\b/g,'window.__atlasLocation')+'\n}).call(window,window.__atlasLocation,window.__atlasHistory);';
    }
    const start=doc.createElement('script');start.textContent='('+bridge.toString()+')();';doc.head.prepend(start);
    return '<!DOCTYPE html>\n'+doc.documentElement.outerHTML;
  }
  function render(){
    const {page}=select();if(!hasPage(page)){error.hidden=false;error.textContent='This page is not included. Remove the page selection to open the overview.';frame.hidden=true;return;}
    error.hidden=true;frame.hidden=false;
    if(page===active){frame.contentWindow?.dispatchEvent(new Event('hashchange'));return;}
    active=page;frame.srcdoc=hydrate(page);
  }
  window.__atlasNavigate=function(page,search,hash){if(!hasPage(page))return;writeState({page,query:search||'?theme=light',hash:hash||''},false);if(page===active)active=null;render();};
  frame.addEventListener('load',()=>{try{document.title=frame.contentDocument.title;frame.title=frame.contentDocument.title;}catch(_){}});
  addEventListener('popstate',render);addEventListener('hashchange',render);
  try{render();}catch(e){error.hidden=false;error.textContent='The embedded atlas could not open: '+e.message;frame.hidden=true;}
}

export async function renderStandaloneAtlas(plan) {
  if (
    !plan ||
    Object.keys(plan).sort().join(",") !== "atlas,output" ||
    !path.isAbsolute(plan.output ?? "")
  )
    throw Error("Explicit standalone atlas and output required");
  const selected = await readEthosAtlasOutput(plan.atlas);
  const html = Buffer.from(composeStandaloneAtlas(selected));
  const parent = path.dirname(plan.output);
  if ((await fs.realpath(parent)) !== parent || (await fs.lstat(parent)).isSymbolicLink())
    throw Error("Physical standalone output parent required");
  await fs.writeFile(plan.output, html, { flag: "wx" });
  return {
    status: "rendered",
    output: plan.output,
    pages: selected.pages.length,
    sha256: sha256(html),
    bytes: html.length,
    atlasManifestSha256: selected.manifestSha256,
    browserAcceptance: "not-performed",
    semanticAcceptance: "not-performed",
  };
}
