import{Ht as e,On as t,Yt as n,b as r,ct as i,it as a,mt as o,v as s,vn as c}from"./runtime-core.esm-bundler-CaODJcyn.js";import{S as l}from"./runtime-dom.esm-bundler-CngAXjEY.js";import{v as u}from"./dist-Ch2WWpyb.js";import{t as d}from"./_plugin-vue_export-helper-BDNMzG2s.js";import{t as f}from"./FilePreviewSkeleton-DRmyefud.js";import{t as p}from"./useEmitter-D8mTgEN5.js";var m=[`src`],h=d({__name:`ImagePreview`,props:{previewEntity:Object},setup(d){let h=d,g=c(!0),_=c(null),v=u(_);e(h.previewEntity,()=>{g.value=!0,_.value=null,y()});async function y(){g.value=!0;let e={Accept:`application/json`,"Content-Type":`application/json; charset=utf-8`,"X-Frappe-Site-Name":window.location.hostname},t=await fetch(`/api/method/suite.drive.api.files.get_file_content?entity_name=${h.previewEntity.name}`,{method:`GET`,headers:e});t.ok&&(_.value=await t.blob(),g.value=!1)}return p(`printFile`,()=>{let e=document.createElement(`iframe`);e.style.position=`absolute`,e.style.width=`0`,e.style.height=`0`,e.style.border=`none`,document.body.appendChild(e),e.contentWindow.document.open(),e.contentWindow.document.write(`
    <html>
      <head>
        <style>
          img {
            max-width: 100%;
            height: auto;
          }
        </style>
      </head>
      <body>
        <img src="${v.value}" />
      </body>
    </html>
  `),e.contentWindow.document.close(),e.contentWindow.focus(),e.contentWindow.print(),e.onload=()=>{setTimeout(()=>{document.body.removeChild(e)},100)}}),e(()=>h.previewEntity,()=>{y()}),i(()=>{y()}),a(()=>{g.value=!0,_.value=null}),(e,i)=>g.value?(o(),s(f,{key:0})):n((o(),r(`img`,{key:1,draggable:`false`,class:`self-center justify-center max-h-[70vh] max-w-full rounded-6`,src:t(v)},null,8,m)),[[l,!g.value]])}},[[`__scopeId`,`data-v-6ddb2485`]]);export{h as default};