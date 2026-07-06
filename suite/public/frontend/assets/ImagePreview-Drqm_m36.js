import{Ct as e,Mt as t,N as n,S as r,V as i,W as a,b as o,c as s,dt as c,ot as l,q as u}from"./vue.runtime.esm-bundler-DwZq-8QY.js";import{g as d}from"./core-BiaryMVd.js";import{t as f}from"./_plugin-vue_export-helper-BDNMzG2s.js";import{t as p}from"./LoadingIndicator-CPVrI1r7.js";var m=[`src`],h=f({__name:`ImagePreview`,props:{previewEntity:Object},setup(f){let h=f,g=e(!0),_=e(null),v=d(_),y=n(`emitter`);l(h.previewEntity,()=>{g.value=!0,_.value=null,b()});async function b(){g.value=!0;let e={Accept:`application/json`,"Content-Type":`application/json; charset=utf-8`,"X-Frappe-Site-Name":window.location.hostname},t=await fetch(`/api/method/suite.drive.api.files.get_file_content?entity_name=${h.previewEntity.name}`,{method:`GET`,headers:e});t.ok&&(_.value=await t.blob(),g.value=!1)}return y.on(`printFile`,()=>{let e=document.createElement(`iframe`);e.style.position=`absolute`,e.style.width=`0`,e.style.height=`0`,e.style.border=`none`,document.body.appendChild(e),e.contentWindow.document.open(),e.contentWindow.document.write(`
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
  `),e.contentWindow.document.close(),e.contentWindow.focus(),e.contentWindow.print(),e.onload=()=>{setTimeout(()=>{document.body.removeChild(e)},100)}}),l(()=>h.previewEntity,()=>{b()}),a(()=>{b()}),i(()=>{y.off(`printFile`),g.value=!0,_.value=null}),(e,n)=>g.value?(u(),o(t(p),{key:0,class:`w-10`})):c((u(),r(`img`,{key:1,draggable:`false`,class:`self-center justify-center max-h-[70vh] max-w-full rounded-lg`,src:t(v)},null,8,m)),[[s,!g.value]])}},[[`__scopeId`,`data-v-514a91b5`]]);export{h as default};