var us=Object.defineProperty;var ms=(i,t,e)=>t in i?us(i,t,{enumerable:!0,configurable:!0,writable:!0,value:e}):i[t]=e;var m=(i,t,e)=>ms(i,typeof t!="symbol"?t+"":t,e);var ft="domo-thermostat-card",Rt="domo-thermostat-card-editor",zt=["climate","water_heater"],xe="M12,16A2,2 0 0,1 14,18A2,2 0 0,1 12,20A2,2 0 0,1 10,18A2,2 0 0,1 12,16M12,10A2,2 0 0,1 14,12A2,2 0 0,1 12,14A2,2 0 0,1 10,12A2,2 0 0,1 12,10M12,4A2,2 0 0,1 14,6A2,2 0 0,1 12,8A2,2 0 0,1 10,6A2,2 0 0,1 12,4Z",we="ha-state-control-climate-temperature",Se="ha-state-control-water_heater-temperature",Pt="Jolly",N="var(--state-climate-jolly-color, #ffd600)",Y=["monday","tuesday","wednesday","thursday","friday","saturday","sunday","jolly"],Nt=[15,30,60],It=60,ie=["auto","jolly","heat_cool","heat","cool","dry","fan_only","off"],Ht={auto:"mdi:thermostat-auto",jolly:"mdi:star-outline",heat_cool:"mdi:sun-snowflake-variant",heat:"mdi:fire",cool:"mdi:snowflake",dry:"mdi:water-percent",fan_only:"mdi:fan",off:"mdi:power"},gt="domo-thermostat-minimal-card",jt="domo-thermostat-minimal-card-editor",Ee=.1656,Ae={auto:"Auto",jolly:"Jolly",heat:"Man",cool:"Man",off:"Off"},Ce={auto:"mdi:fan-auto",low:"mdi:fan-speed-1",medium:"mdi:fan-speed-2",high:"mdi:fan-speed-3"};var Ut=globalThis,Dt=Ut.ShadowRoot&&(Ut.ShadyCSS===void 0||Ut.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,oe=Symbol(),Oe=new WeakMap,yt=class{constructor(t,e,s){if(this._$cssResult$=!0,s!==oe)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(Dt&&t===void 0){let s=e!==void 0&&e.length===1;s&&(t=Oe.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),s&&Oe.set(e,t))}return t}toString(){return this.cssText}},Te=i=>new yt(typeof i=="string"?i:i+"",void 0,oe),_=(i,...t)=>{let e=i.length===1?i[0]:t.reduce((s,o,r)=>s+(n=>{if(n._$cssResult$===!0)return n.cssText;if(typeof n=="number")return n;throw Error("Value passed to 'css' function must be a 'css' function result: "+n+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(o)+i[r+1],i[0]);return new yt(e,i,oe)},ke=(i,t)=>{if(Dt)i.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let s=document.createElement("style"),o=Ut.litNonce;o!==void 0&&s.setAttribute("nonce",o),s.textContent=e.cssText,i.appendChild(s)}},re=Dt?i=>i:i=>i instanceof CSSStyleSheet?(t=>{let e="";for(let s of t.cssRules)e+=s.cssText;return Te(e)})(i):i;var{is:fs,defineProperty:gs,getOwnPropertyDescriptor:ys,getOwnPropertyNames:_s,getOwnPropertySymbols:vs,getPrototypeOf:bs}=Object,k=globalThis,Me=k.trustedTypes,$s=Me?Me.emptyScript:"",xs=k.reactiveElementPolyfillSupport,_t=(i,t)=>i,ne={toAttribute(i,t){switch(t){case Boolean:i=i?$s:null;break;case Object:case Array:i=i==null?i:JSON.stringify(i)}return i},fromAttribute(i,t){let e=i;switch(t){case Boolean:e=i!==null;break;case Number:e=i===null?null:Number(i);break;case Object:case Array:try{e=JSON.parse(i)}catch{e=null}}return e}},Re=(i,t)=>!fs(i,t),Le={attribute:!0,type:String,converter:ne,reflect:!1,useDefault:!1,hasChanged:Re};Symbol.metadata??(Symbol.metadata=Symbol("metadata")),k.litPropertyMetadata??(k.litPropertyMetadata=new WeakMap);var T=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??(this.l=[])).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=Le){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let s=Symbol(),o=this.getPropertyDescriptor(t,s,e);o!==void 0&&gs(this.prototype,t,o)}}static getPropertyDescriptor(t,e,s){let{get:o,set:r}=ys(this.prototype,t)??{get(){return this[e]},set(n){this[e]=n}};return{get:o,set(n){let l=o?.call(this);r?.call(this,n),this.requestUpdate(t,l,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??Le}static _$Ei(){if(this.hasOwnProperty(_t("elementProperties")))return;let t=bs(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(_t("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(_t("properties"))){let e=this.properties,s=[..._s(e),...vs(e)];for(let o of s)this.createProperty(o,e[o])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[s,o]of e)this.elementProperties.set(s,o)}this._$Eh=new Map;for(let[e,s]of this.elementProperties){let o=this._$Eu(e,s);o!==void 0&&this._$Eh.set(o,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let s=new Set(t.flat(1/0).reverse());for(let o of s)e.unshift(re(o))}else t!==void 0&&e.push(re(t));return e}static _$Eu(t,e){let s=e.attribute;return s===!1?void 0:typeof s=="string"?s:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??(this._$EO=new Set)).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let s of e.keys())this.hasOwnProperty(s)&&(t.set(s,this[s]),delete this[s]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return ke(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??(this.renderRoot=this.createRenderRoot()),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,s){this._$AK(t,s)}_$ET(t,e){let s=this.constructor.elementProperties.get(t),o=this.constructor._$Eu(t,s);if(o!==void 0&&s.reflect===!0){let r=(s.converter?.toAttribute!==void 0?s.converter:ne).toAttribute(e,s.type);this._$Em=t,r==null?this.removeAttribute(o):this.setAttribute(o,r),this._$Em=null}}_$AK(t,e){let s=this.constructor,o=s._$Eh.get(t);if(o!==void 0&&this._$Em!==o){let r=s.getPropertyOptions(o),n=typeof r.converter=="function"?{fromAttribute:r.converter}:r.converter?.fromAttribute!==void 0?r.converter:ne;this._$Em=o;let l=n.fromAttribute(e,r.type);this[o]=l??this._$Ej?.get(o)??l,this._$Em=null}}requestUpdate(t,e,s,o=!1,r){if(t!==void 0){let n=this.constructor;if(o===!1&&(r=this[t]),s??(s=n.getPropertyOptions(t)),!((s.hasChanged??Re)(r,e)||s.useDefault&&s.reflect&&r===this._$Ej?.get(t)&&!this.hasAttribute(n._$Eu(t,s))))return;this.C(t,e,s)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:s,reflect:o,wrapped:r},n){s&&!(this._$Ej??(this._$Ej=new Map)).has(t)&&(this._$Ej.set(t,n??e??this[t]),r!==!0||n!==void 0)||(this._$AL.has(t)||(this.hasUpdated||s||(e=void 0),this._$AL.set(t,e)),o===!0&&this._$Em!==t&&(this._$Eq??(this._$Eq=new Set)).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??(this.renderRoot=this.createRenderRoot()),this._$Ep){for(let[o,r]of this._$Ep)this[o]=r;this._$Ep=void 0}let s=this.constructor.elementProperties;if(s.size>0)for(let[o,r]of s){let{wrapped:n}=r,l=this[o];n!==!0||this._$AL.has(o)||l===void 0||this.C(o,void 0,r,l)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(s=>s.hostUpdate?.()),this.update(e)):this._$EM()}catch(s){throw t=!1,this._$EM(),s}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&(this._$Eq=this._$Eq.forEach(e=>this._$ET(e,this[e]))),this._$EM()}updated(t){}firstUpdated(t){}};T.elementStyles=[],T.shadowRootOptions={mode:"open"},T[_t("elementProperties")]=new Map,T[_t("finalized")]=new Map,xs?.({ReactiveElement:T}),(k.reactiveElementVersions??(k.reactiveElementVersions=[])).push("2.1.2");var bt=globalThis,ze=i=>i,Vt=bt.trustedTypes,Pe=Vt?Vt.createPolicy("lit-html",{createHTML:i=>i}):void 0,De="$lit$",M=`lit$${Math.random().toFixed(9).slice(2)}$`,Ve="?"+M,ws=`<${Ve}>`,j=document,$t=()=>j.createComment(""),xt=i=>i===null||typeof i!="object"&&typeof i!="function",ue=Array.isArray,Ss=i=>ue(i)||typeof i?.[Symbol.iterator]=="function",ae=`[ 	
\f\r]`,vt=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,Ne=/-->/g,Ie=/>/g,I=RegExp(`>|${ae}(?:([^\\s"'>=/]+)(${ae}*=${ae}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),He=/'/g,je=/"/g,Be=/^(?:script|style|textarea|title)$/i,me=i=>(t,...e)=>({_$litType$:i,strings:t,values:e}),c=me(1),di=me(2),pi=me(3),E=Symbol.for("lit-noChange"),h=Symbol.for("lit-nothing"),Ue=new WeakMap,H=j.createTreeWalker(j,129);function qe(i,t){if(!ue(i)||!i.hasOwnProperty("raw"))throw Error("invalid template strings array");return Pe!==void 0?Pe.createHTML(t):t}var Es=(i,t)=>{let e=i.length-1,s=[],o,r=t===2?"<svg>":t===3?"<math>":"",n=vt;for(let l=0;l<e;l++){let a=i[l],p,d,u=-1,x=0;for(;x<a.length&&(n.lastIndex=x,d=n.exec(a),d!==null);)x=n.lastIndex,n===vt?d[1]==="!--"?n=Ne:d[1]!==void 0?n=Ie:d[2]!==void 0?(Be.test(d[2])&&(o=RegExp("</"+d[2],"g")),n=I):d[3]!==void 0&&(n=I):n===I?d[0]===">"?(n=o??vt,u=-1):d[1]===void 0?u=-2:(u=n.lastIndex-d[2].length,p=d[1],n=d[3]===void 0?I:d[3]==='"'?je:He):n===je||n===He?n=I:n===Ne||n===Ie?n=vt:(n=I,o=void 0);let S=n===I&&i[l+1].startsWith("/>")?" ":"";r+=n===vt?a+ws:u>=0?(s.push(p),a.slice(0,u)+De+a.slice(u)+M+S):a+M+(u===-2?l:S)}return[qe(i,r+(i[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),s]},wt=class i{constructor({strings:t,_$litType$:e},s){let o;this.parts=[];let r=0,n=0,l=t.length-1,a=this.parts,[p,d]=Es(t,e);if(this.el=i.createElement(p,s),H.currentNode=this.el.content,e===2||e===3){let u=this.el.content.firstChild;u.replaceWith(...u.childNodes)}for(;(o=H.nextNode())!==null&&a.length<l;){if(o.nodeType===1){if(o.hasAttributes())for(let u of o.getAttributeNames())if(u.endsWith(De)){let x=d[n++],S=o.getAttribute(u).split(M),z=/([.?@])?(.*)/.exec(x);a.push({type:1,index:r,name:z[2],strings:S,ctor:z[1]==="."?ce:z[1]==="?"?he:z[1]==="@"?de:G}),o.removeAttribute(u)}else u.startsWith(M)&&(a.push({type:6,index:r}),o.removeAttribute(u));if(Be.test(o.tagName)){let u=o.textContent.split(M),x=u.length-1;if(x>0){o.textContent=Vt?Vt.emptyScript:"";for(let S=0;S<x;S++)o.append(u[S],$t()),H.nextNode(),a.push({type:2,index:++r});o.append(u[x],$t())}}}else if(o.nodeType===8)if(o.data===Ve)a.push({type:2,index:r});else{let u=-1;for(;(u=o.data.indexOf(M,u+1))!==-1;)a.push({type:7,index:r}),u+=M.length-1}r++}}static createElement(t,e){let s=j.createElement("template");return s.innerHTML=t,s}};function W(i,t,e=i,s){if(t===E)return t;let o=s!==void 0?e._$Co?.[s]:e._$Cl,r=xt(t)?void 0:t._$litDirective$;return o?.constructor!==r&&(o?._$AO?.(!1),r===void 0?o=void 0:(o=new r(i),o._$AT(i,e,s)),s!==void 0?(e._$Co??(e._$Co=[]))[s]=o:e._$Cl=o),o!==void 0&&(t=W(i,o._$AS(i,t.values),o,s)),t}var le=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:s}=this._$AD,o=(t?.creationScope??j).importNode(e,!0);H.currentNode=o;let r=H.nextNode(),n=0,l=0,a=s[0];for(;a!==void 0;){if(n===a.index){let p;a.type===2?p=new St(r,r.nextSibling,this,t):a.type===1?p=new a.ctor(r,a.name,a.strings,this,t):a.type===6&&(p=new pe(r,this,t)),this._$AV.push(p),a=s[++l]}n!==a?.index&&(r=H.nextNode(),n++)}return H.currentNode=j,o}p(t){let e=0;for(let s of this._$AV)s!==void 0&&(s.strings!==void 0?(s._$AI(t,s,e),e+=s.strings.length-2):s._$AI(t[e])),e++}},St=class i{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,s,o){this.type=2,this._$AH=h,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=s,this.options=o,this._$Cv=o?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=W(this,t,e),xt(t)?t===h||t==null||t===""?(this._$AH!==h&&this._$AR(),this._$AH=h):t!==this._$AH&&t!==E&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):Ss(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==h&&xt(this._$AH)?this._$AA.nextSibling.data=t:this.T(j.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:s}=t,o=typeof s=="number"?this._$AC(t):(s.el===void 0&&(s.el=wt.createElement(qe(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===o)this._$AH.p(e);else{let r=new le(o,this),n=r.u(this.options);r.p(e),this.T(n),this._$AH=r}}_$AC(t){let e=Ue.get(t.strings);return e===void 0&&Ue.set(t.strings,e=new wt(t)),e}k(t){ue(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,s,o=0;for(let r of t)o===e.length?e.push(s=new i(this.O($t()),this.O($t()),this,this.options)):s=e[o],s._$AI(r),o++;o<e.length&&(this._$AR(s&&s._$AB.nextSibling,o),e.length=o)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let s=ze(t).nextSibling;ze(t).remove(),t=s}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},G=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,s,o,r){this.type=1,this._$AH=h,this._$AN=void 0,this.element=t,this.name=e,this._$AM=o,this.options=r,s.length>2||s[0]!==""||s[1]!==""?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=h}_$AI(t,e=this,s,o){let r=this.strings,n=!1;if(r===void 0)t=W(this,t,e,0),n=!xt(t)||t!==this._$AH&&t!==E,n&&(this._$AH=t);else{let l=t,a,p;for(t=r[0],a=0;a<r.length-1;a++)p=W(this,l[s+a],e,a),p===E&&(p=this._$AH[a]),n||(n=!xt(p)||p!==this._$AH[a]),p===h?t=h:t!==h&&(t+=(p??"")+r[a+1]),this._$AH[a]=p}n&&!o&&this.j(t)}j(t){t===h?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},ce=class extends G{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===h?void 0:t}},he=class extends G{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==h)}},de=class extends G{constructor(t,e,s,o,r){super(t,e,s,o,r),this.type=5}_$AI(t,e=this){if((t=W(this,t,e,0)??h)===E)return;let s=this._$AH,o=t===h&&s!==h||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,r=t!==h&&(s===h||o);o&&this.element.removeEventListener(this.name,this,s),r&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},pe=class{constructor(t,e,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(t){W(this,t)}};var As=bt.litHtmlPolyfillSupport;As?.(wt,St),(bt.litHtmlVersions??(bt.litHtmlVersions=[])).push("3.3.3");var Je=(i,t,e)=>{let s=e?.renderBefore??t,o=s._$litPart$;if(o===void 0){let r=e?.renderBefore??null;s._$litPart$=o=new St(t.insertBefore($t(),r),r,void 0,e??{})}return o._$AI(i),o};var Et=globalThis,g=class extends T{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){var e;let t=super.createRenderRoot();return(e=this.renderOptions).renderBefore??(e.renderBefore=t.firstChild),t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=Je(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return E}};g._$litElement$=!0,g.finalized=!0,Et.litElementHydrateSupport?.({LitElement:g});var Cs=Et.litElementPolyfillSupport;Cs?.({LitElement:g});(Et.litElementVersions??(Et.litElementVersions=[])).push("4.2.2");var Bt=i=>i.split(".")[0];function L(i,t,e={}){i.dispatchEvent(new CustomEvent(t,{detail:e,bubbles:!0,composed:!0}))}function Z(i,t,e){if(typeof i.formatEntityName=="function")try{return i.formatEntityName(t,e)}catch{}return typeof e=="string"&&e?e:t.attributes.friendly_name??t.entity_id}function Ye(i){let t=Bt(i.entity_id);return i.state==="unavailable"?"var(--state-unavailable-color)":i.state==="unknown"?"var(--state-unknown-color)":i.state==="off"?`var(--state-${t}-off-color, var(--state-inactive-color))`:`var(--state-${t}-${i.state}-color, var(--state-${t}-active-color, var(--state-active-color)))`}function qt(i,t){return i.localize("ui.panel.lovelace.warning.entity_not_found",{entity:t||"[empty]"})}function Jt(i,t,e){if((i.__appliedThemeVars||[]).forEach(p=>i.style.removeProperty(p)),i.__appliedThemeVars=[],!e||e==="default"||!t?.themes?.[e])return;let o=t.themes[e],r=t.darkMode,{modes:n,...l}=o,a={...l,...n?n[r?"dark":"light"]:{}};Object.entries(a).forEach(([p,d])=>{let u=`--${p}`;i.style.setProperty(u,String(d)),i.__appliedThemeVars.push(u)})}async function At(i){let t=["ha-card","ha-icon-button",we,Se],e=()=>t.filter(o=>!customElements.get(o));if(!e().length)return;try{(await window.loadCardHelpers?.())?.createCardElement({type:"thermostat",entity:i})}catch{}let s=new Promise(o=>setTimeout(o,5e3));await Promise.race([Promise.all(e().map(o=>customElements.whenDefined(o))),s])}var K=null;function Ft(i,t){let e=i?.shadowRoot;if(!e||!("adoptedStyleSheets"in e))return;K||(K=new CSSStyleSheet,K.replaceSync(`ha-control-circular-slider{--control-circular-slider-color:${N} !important;--control-circular-slider-low-color:${N} !important;--control-circular-slider-high-color:${N} !important;--state-color:${N} !important;}`));let s=e.adoptedStyleSheets.includes(K);t&&!s?e.adoptedStyleSheets=[...e.adoptedStyleSheets,K]:!t&&s&&(e.adoptedStyleSheets=e.adoptedStyleSheets.filter(o=>o!==K))}function Yt(i,t,e){if(!i||!t||!e)return;let s=i.getBoundingClientRect(),o=t.getBoundingClientRect(),r=Math.max(0,o.width-16),n=o.top-s.top+8+r/2;e.style.left=`${o.left-s.left+o.width/2}px`,e.style.top=`${n-2*Ee*r}px`}var We={heating:"mdi:fire",cooling:"mdi:snowflake",drying:"mdi:water-percent",fan:"mdi:fan",idle:"mdi:clock-outline",off:"mdi:power",preheating:"mdi:heat-wave",defrosting:"mdi:snowflake-melt"},fe="var(--state-climate-heat-color, #ff8100)",Os="var(--state-climate-cool-color, #2b9af9)",Fe="var(--state-inactive-color, #9e9e9e)",Ts={heating:fe,preheating:fe,defrosting:fe,cooling:Os,drying:"var(--state-climate-dry-color, #efbd07)",fan:"var(--state-climate-fan_only-color, #8ac24a)",idle:Fe,off:Fe},Ge=i=>Ts[i]||null;var Ke={it:{monday:"LUN",tuesday:"MAR",wednesday:"MER",thursday:"GIO",friday:"VEN",saturday:"SAB",sunday:"DOM",jolly:"JOLLY",copy:"Copia",copyTo:"Copia su",apply:"Applica",cancel:"Annulla",copyTitle:"Copia {day} su:",dayTitle:"Seleziona il giorno",save:"Salva",saveClose:"Salva e chiudi",closeNoSave:"Chiudi senza salvare",program:"Crono",zoomIn:"Ingrandisci",hour:"Ora",fan:"Fan",showJolly:"Mostra il pulsante Jolly",jollyLabel:"Jolly",curTemp:"Temperatura attuale",curHum:"Umidit\xE0 attuale",close:"Chiudi",history:"Storico",settings:"Impostazioni",more:"Altro",missing:"Aggiorna climate.py: mancano i dati del profilo"},en:{monday:"MON",tuesday:"TUE",wednesday:"WED",thursday:"THU",friday:"FRI",saturday:"SAT",sunday:"SUN",jolly:"JOLLY",copy:"Copy",copyTo:"Copy to",apply:"Apply",cancel:"Cancel",copyTitle:"Copy {day} to:",dayTitle:"Select day",save:"Save",saveClose:"Save and close",closeNoSave:"Close without saving",program:"Sched.",zoomIn:"Zoom",hour:"Hour",fan:"Fan",showJolly:"Show the Jolly button",jollyLabel:"Jolly",curTemp:"Current temperature",curHum:"Current humidity",close:"Close",history:"History",settings:"Settings",more:"More",missing:"Update climate.py: profile data missing"},de:{monday:"MO",tuesday:"DI",wednesday:"MI",thursday:"DO",friday:"FR",saturday:"SA",sunday:"SO",jolly:"JOLLY",copy:"Kopieren",copyTo:"Kopieren auf",apply:"\xDCbernehmen",cancel:"Abbrechen",copyTitle:"{day} kopieren auf:",dayTitle:"Tag w\xE4hlen",save:"Speichern",saveClose:"Speichern und schlie\xDFen",closeNoSave:"Schlie\xDFen ohne Speichern",program:"Zeitpl.",zoomIn:"Vergr\xF6\xDFern",hour:"Stunde",fan:"L\xFCfter",showJolly:"Jolly-Taste anzeigen",jollyLabel:"Jolly",curTemp:"Aktuelle Temperatur",curHum:"Aktuelle Luftfeuchtigkeit",close:"Schlie\xDFen",history:"Verlauf",settings:"Einstellungen",more:"Mehr",missing:"climate.py aktualisieren: Profildaten fehlen"},es:{monday:"LUN",tuesday:"MAR",wednesday:"MI\xC9",thursday:"JUE",friday:"VIE",saturday:"S\xC1B",sunday:"DOM",jolly:"JOLLY",copy:"Copiar",copyTo:"Copiar en",apply:"Aplicar",cancel:"Cancelar",copyTitle:"Copiar {day} en:",dayTitle:"Elegir d\xEDa",save:"Guardar",saveClose:"Guardar y cerrar",closeNoSave:"Cerrar sin guardar",program:"Prog.",zoomIn:"Ampliar",hour:"Hora",fan:"Ventilador",showJolly:"Mostrar el bot\xF3n Jolly",jollyLabel:"Jolly",curTemp:"Temperatura actual",curHum:"Humedad actual",close:"Cerrar",history:"Historial",settings:"Ajustes",more:"M\xE1s",missing:"Actualiza climate.py: faltan los datos del perfil"},fr:{monday:"LUN",tuesday:"MAR",wednesday:"MER",thursday:"JEU",friday:"VEN",saturday:"SAM",sunday:"DIM",jolly:"JOLLY",copy:"Copier",copyTo:"Copier vers",apply:"Appliquer",cancel:"Annuler",copyTitle:"Copier {day} vers :",dayTitle:"Choisir le jour",save:"Enregistrer",saveClose:"Enregistrer et fermer",closeNoSave:"Fermer sans enregistrer",program:"Prog.",zoomIn:"Agrandir",hour:"Heure",fan:"Ventilateur",showJolly:"Afficher le bouton Jolly",jollyLabel:"Jolly",curTemp:"Temp\xE9rature actuelle",curHum:"Humidit\xE9 actuelle",close:"Fermer",history:"Historique",settings:"Param\xE8tres",more:"Plus",missing:"Mettez \xE0 jour climate.py : donn\xE9es du profil manquantes"},ru:{monday:"\u041F\u041D",tuesday:"\u0412\u0422",wednesday:"\u0421\u0420",thursday:"\u0427\u0422",friday:"\u041F\u0422",saturday:"\u0421\u0411",sunday:"\u0412\u0421",jolly:"JOLLY",copy:"\u041A\u043E\u043F\u0438\u0440\u043E\u0432\u0430\u0442\u044C",copyTo:"\u041A\u043E\u043F\u0438\u0440\u043E\u0432\u0430\u0442\u044C \u043D\u0430",apply:"\u041F\u0440\u0438\u043C\u0435\u043D\u0438\u0442\u044C",cancel:"\u041E\u0442\u043C\u0435\u043D\u0430",copyTitle:"\u041A\u043E\u043F\u0438\u0440\u043E\u0432\u0430\u0442\u044C {day} \u043D\u0430:",dayTitle:"\u0412\u044B\u0431\u0435\u0440\u0438\u0442\u0435 \u0434\u0435\u043D\u044C",save:"\u0421\u043E\u0445\u0440\u0430\u043D\u0438\u0442\u044C",saveClose:"\u0421\u043E\u0445\u0440\u0430\u043D\u0438\u0442\u044C \u0438 \u0437\u0430\u043A\u0440\u044B\u0442\u044C",closeNoSave:"\u0417\u0430\u043A\u0440\u044B\u0442\u044C \u0431\u0435\u0437 \u0441\u043E\u0445\u0440\u0430\u043D\u0435\u043D\u0438\u044F",program:"\u041F\u0440\u043E\u0433\u0440.",zoomIn:"\u0423\u0432\u0435\u043B\u0438\u0447\u0438\u0442\u044C",hour:"\u0427\u0430\u0441",fan:"\u0412\u0435\u043D\u0442\u0438\u043B\u044F\u0442\u043E\u0440",showJolly:"\u041F\u043E\u043A\u0430\u0437\u0430\u0442\u044C \u043A\u043D\u043E\u043F\u043A\u0443 Jolly",jollyLabel:"Jolly",curTemp:"\u0422\u0435\u043A\u0443\u0449\u0430\u044F \u0442\u0435\u043C\u043F\u0435\u0440\u0430\u0442\u0443\u0440\u0430",curHum:"\u0422\u0435\u043A\u0443\u0449\u0430\u044F \u0432\u043B\u0430\u0436\u043D\u043E\u0441\u0442\u044C",close:"\u0417\u0430\u043A\u0440\u044B\u0442\u044C",history:"\u0418\u0441\u0442\u043E\u0440\u0438\u044F",settings:"\u041D\u0430\u0441\u0442\u0440\u043E\u0439\u043A\u0438",more:"\u0415\u0449\u0451",missing:"\u041E\u0431\u043D\u043E\u0432\u0438\u0442\u0435 climate.py: \u043D\u0435\u0442 \u0434\u0430\u043D\u043D\u044B\u0445 \u043F\u0440\u043E\u0444\u0438\u043B\u044F"}},Ze=i=>{let t=String(i?.language||"it").toLowerCase().split(/[-_]/)[0];return Ke[t]?t:"en"},f=(i,t)=>Ke[Ze(i)][t]??t,ks={low:"Basso",medium:"Medio",high:"Alto"},Xe=(i,t)=>Ze(i)==="it"?ks[t]:void 0;var X=i=>i.attributes.preset_mode===Pt||i.attributes.mode==="jolly",ge=i=>(i.attributes.preset_modes||[]).includes(Pt);function Qe(i){let t=i?.attributes?.hvac_modes||[],e=t.includes("cool"),s=t.includes("heat");return e&&!s?!0:e&&s?i.state==="cool"||i.attributes.hvac_action==="cooling":!1}var Ct=i=>X(i)?"jolly":i.state;function Ms(i,t,e){if(e==="jolly")return f(i,"jollyLabel");let s=i.formatEntityState?.(t,e);return s||e.charAt(0).toUpperCase()+e.slice(1).replace(/_/g," ")}function ts(i,t,e,s=!1){let o=e?.hvac_modes,r=(t.attributes.hvac_modes||[]).filter(l=>!o||o.includes(l));ge(t)&&(!o||o.includes("jolly"))&&(r=[...r,"jolly"]);let n=l=>{let a=ie.indexOf(l);return a===-1?ie.length:a};return r.sort((l,a)=>n(l)-n(a)).map(l=>({value:l,label:s&&Ae[l]||Ms(i,t,l),icon:Ht[l]||"mdi:thermostat"}))}function Wt(i,t){return t==="jolly"?["climate","set_preset_mode",{entity_id:i,preset_mode:Pt}]:["climate","set_hvac_mode",{entity_id:i,hvac_mode:t}]}var Gt=72,y=[256,256,328,400,472],Ls=228,Q=_`
  :host {
    --season: var(--state-climate-heat-color, #ff8100);
  }
  :host([season="summer"]) {
    --season: var(--state-climate-cool-color, #2b9af9);
  }
  :host {
    --lvl1: color-mix(in srgb, var(--season) 50%, transparent);
    --lvl2: var(--lvl1);
    --lvl3: var(--lvl1);
  }
`,es=1.5,tt={1:"1",2:"3",3:"5"},Rs={1:1,2:1,3:2,4:2,5:3},U=3.75,$=(i,t)=>{let e=t*Math.PI/180;return[i*Math.sin(e),-i*Math.cos(e)]},v=i=>i.toFixed(2),D=(i,t,e,s)=>{let[o,r]=$(t,e),[n,l]=$(t,s),[a,p]=$(i,s),[d,u]=$(i,e),x=s-e>180?1:0;return`M${v(o)} ${v(r)}A${t} ${t} 0 ${x} 1 ${v(n)} ${v(l)}L${v(a)} ${v(p)}A${i} ${i} 0 ${x} 0 ${v(d)} ${v(u)}Z`},_e=i=>Rs[i]||1,ss=i=>typeof i=="string"&&i.length===96,is=(()=>{let i="";for(let t=0;t<24;t++){let[e,s]=$(Ls,t*15);i+=`<text x="${v(e)}" y="${v(s)}">${t}</text>`}return i})(),ye=Math.PI/180,zs=(i,t,e)=>{let s=(t-i)/2,o=Math.sin(e*ye/2),r=i*o/(1-o),n=(i+t)/2*e*ye/2;return Math.max(0,Math.min(s,n,r*.98))},Ot=(i,t,e,s,o=!0,r=!0)=>{let n=zs(i,t,s-e),l=o?n:0,a=r?n:0,p=(P,O,se)=>Math.asin(O/(se?P-O:P+O))/ye,d=(P,O,se)=>{let $e=se?P-O:P+O;return Math.sqrt($e*$e-O*O)},u=(P,O)=>$(P,O).map(v).join(" "),x=e+(l>0?p(t,l,!0):0),S=s-(a>0?p(t,a,!0):0),z=e+(l>0?p(i,l,!1):0),be=s-(a>0?p(i,a,!1):0),F=l>0?`M${u(d(t,l,!0),e)}A${v(l)} ${v(l)} 0 0 1 ${u(t,x)}`:`M${u(t,e)}`;return F+=`A${t} ${t} 0 ${S-x>180?1:0} 1 ${u(t,S)}`,a>0?F+=`A${v(a)} ${v(a)} 0 0 1 ${u(d(t,a,!0),s)}L${u(d(i,a,!1),s)}A${v(a)} ${v(a)} 0 0 1 ${u(i,be)}`:F+=`L${u(i,s)}`,F+=`A${i} ${i} 0 ${be-z>180?1:0} 0 ${u(i,z)}`,l>0&&(F+=`A${v(l)} ${v(l)} 0 0 1 ${u(d(i,l,!1),e)}`),`${F}Z`},os=i=>{let t=i.length,e=i.map(_e),s=-1;for(let n=0;n<t;n++)if(e[n]!==e[(n+t-1)%t]){s=n;break}if(s<0)return[{lvl:e[0],start:0,len:t,full:!0}];let o=[],r=null;for(let n=0;n<t;n++){let l=(s+n)%t;r&&r.lvl===e[l]?r.len++:(r={lvl:e[l],start:l,len:1},o.push(r))}return o};var Kt=_`
  :host {
    display: block;
    width: 100%;
  }
  button {
    font: inherit;
    color: inherit;
    border: 0;
    padding: 0;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
  }
  .row {
    position: relative;
    display: flex;
    align-items: center;
    gap: 12px;
    box-sizing: border-box;
    width: 100%;
    height: var(--feature-height, 42px);
    padding: 0 12px;
    border-radius: var(--feature-border-radius, 12px);
    background: none;
    overflow: hidden;
    text-align: start;
    color: var(--primary-text-color);
    line-height: var(--ha-line-height-condensed, 1.2);
  }
  .row::before {
    content: "";
    position: absolute;
    inset: 0;
    background: var(--disabled-color);
    opacity: 0.2;
    transition: opacity 180ms ease-in-out;
  }
  .row:hover::before {
    opacity: 0.28;
  }
  .row:active::before {
    opacity: 0.36;
  }
  .row > * {
    position: relative;
  }
  .row.center {
    justify-content: center;
    text-align: center;
  }
  .row.center .text {
    align-items: center;
  }
  .row.center .text {
    flex: none;
  }
  ha-icon {
    --mdc-icon-size: 24px;
    flex: none;
    color: var(--secondary-text-color);
  }
  .text {
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-width: 0;
    flex: 1 1 auto;
    font-size: var(--ha-font-size-m, 14px);
    font-weight: var(--ha-font-weight-medium, 500);
  }
  .text > span {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .label {
    font-size: var(--ha-font-size-s, 12px);
    font-weight: var(--ha-font-weight-normal, 400);
    color: var(--secondary-text-color);
  }
`;var et=class extends g{constructor(){super(),this.lines=[],this.center=!1}render(){return c`<button class="row ${this.center?"center":""}">
      ${this.icon?c`<ha-icon .icon=${this.icon}></ha-icon>`:h}
      ${this.lines.length?c`<span class="text" style=${this.center?"flex:none":""}>
            ${this.lines.map((t,e)=>c`<span class=${this.labelFirst&&e===0?"label":""}>${t}</span>`)}
          </span>`:h}
    </button>`}};m(et,"properties",{icon:{type:String},lines:{attribute:!1},center:{type:Boolean},disabled:{type:Boolean,reflect:!0},labelFirst:{type:Boolean,attribute:"label-first"}}),m(et,"styles",[Kt,_`
      :host([disabled]) {
        opacity: 0.4;
        pointer-events: none;
      }
    `]);var st=class extends g{constructor(){super(),this.options=[]}get _current(){return this.options.find(t=>t.value===this.value)}_open(){if(this.disabled)return;let t=this.renderRoot.querySelector(".row"),e=this.renderRoot.querySelector(".menu"),s=t.getBoundingClientRect();e.style.minWidth=`${s.width}px`,e.style.left=`${s.left}px`,e.showPopover();let o=e.offsetHeight,r=window.innerHeight-s.bottom;e.style.top=r<o+8&&s.top>o+8?`${s.top-o-4}px`:`${s.bottom+4}px`}_pick(t){this.renderRoot.querySelector(".menu").hidePopover(),t!==this.value&&this.dispatchEvent(new CustomEvent("selected",{detail:{value:t}}))}render(){let t=this._current,e=this.caption??t?.label??this.value??"";return c`
      <button
        class="row ${this.compact?"center":""}"
        ?disabled=${this.disabled}
        aria-label=${this.label}
        @click=${this._open}
      >
        <ha-icon .icon=${t?.icon||"mdi:thermostat"}></ha-icon>
        ${this.iconOnly?h:c`<span class="text">
              ${this.compact?h:c`<span class="label">${this.label}</span>`}
              <span>${e}</span>
            </span>`}
        ${this.compact?h:c`<ha-icon class="arrow" icon="mdi:menu-down"></ha-icon>`}
      </button>
      <div class="menu" popover="auto">
        ${this.options.map(s=>c`<button
            class="opt ${s.value===this.value?"sel":""}"
            @click=${()=>this._pick(s.value)}
          >
            <ha-icon .icon=${s.icon}></ha-icon><span>${s.label}</span>
          </button>`)}
      </div>
    `}};m(st,"properties",{label:{type:String},options:{attribute:!1},value:{type:String},disabled:{type:Boolean},compact:{type:Boolean},caption:{type:String},iconOnly:{type:Boolean,attribute:"icon-only"}}),m(st,"styles",[Kt,_`
      .arrow {
        margin-inline-start: auto;
      }
      .menu {
        position: fixed;
        inset: auto;
        margin: 0;
        padding: 6px;
        border: 1px solid var(--divider-color, rgba(127, 127, 127, 0.4));
        border-radius: var(--feature-border-radius, 12px);
        background: var(--card-background-color, #fff);
        color: var(--primary-text-color);
        box-shadow: var(--ha-card-box-shadow, 0 6px 24px rgba(0, 0, 0, 0.35));
        max-height: 60vh;
        overflow: auto;
      }
      .menu:popover-open {
        display: flex;
        flex-direction: column;
      }
      .opt {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 12px;
        border-radius: 8px;
        background: none;
        color: var(--primary-text-color);
        font-size: var(--ha-font-size-m, 14px);
        text-align: start;
      }
      .opt:hover {
        background: rgba(var(--rgb-primary-text-color, 127, 127, 127), 0.06);
      }
      .opt.sel {
        color: var(--primary-color);
        background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.14);
      }
      .opt.sel ha-icon {
        color: var(--primary-color);
      }
    `]);var ot=i=>({windowOpen:i?.attributes?.window_open===!0,absent:i?.attributes?.occupied===!1}),it=class extends g{render(){return this.hidden=!this.windowOpen&&!this.absent,c`
      ${this.windowOpen?c`<ha-icon icon="mdi:window-open-variant"></ha-icon>`:h}
      ${this.absent?c`<ha-icon icon="mdi:motion-sensor-off"></ha-icon>`:h}
    `}};m(it,"properties",{windowOpen:{type:Boolean,attribute:"window-open"},absent:{type:Boolean}}),m(it,"styles",_`
    :host {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      color: var(--error-color, #db4437);
      pointer-events: none;
    }
    :host(.floating) {
      position: absolute;
      transform: translate(-50%, -50%);
    }
    :host([hidden]) {
      display: none;
    }
    ha-icon {
      --mdc-icon-size: 24px;
      display: flex;
    }
  `);var rt=class extends g{constructor(){super(),this._selected=new Set}_toggle(t){let e=new Set(this._selected);e.has(t)?e.delete(t):e.add(t),this._selected=e}_fire(t,e){this.dispatchEvent(new CustomEvent(t,{detail:e}))}render(){return c`<div class="panel">
      <div class="title">${f(this.hass,"copyTitle").replace("{day}",f(this.hass,this.day))}</div>
      <div class="chips">
        ${Y.filter(t=>t!==this.day).map(t=>c`<button
            class="chip ${this._selected.has(t)?"on":""}"
            @click=${()=>this._toggle(t)}
          >
            ${f(this.hass,t)}
          </button>`)}
      </div>
      <div class="btns">
        <button class="no" @click=${()=>this._fire("cancel")}>${f(this.hass,"cancel")}</button>
        <button class="ok" @click=${()=>this._fire("apply",[...this._selected])}>
          ${f(this.hass,"apply")}
        </button>
      </div>
    </div>`}};m(rt,"properties",{hass:{attribute:!1},day:{type:String},_selected:{state:!0}}),m(rt,"styles",_`
    :host {
      position: absolute;
      inset: 0;
      z-index: 30;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(0, 0, 0, 0.55);
      border-radius: var(--ha-card-border-radius, 12px);
    }
    .panel {
      width: 86%;
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color);
      border-radius: 16px;
      padding: 20px;
      box-sizing: border-box;
    }
    .title {
      font-size: 1.15rem;
      font-weight: 600;
      text-align: center;
      margin-bottom: 16px;
    }
    .chips {
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 10px;
    }
    button {
      font: inherit;
      color: inherit;
      background: none;
      border: 0;
      cursor: pointer;
    }
    .chip {
      flex: 0 0 calc((100% - 30px) / 4);
      min-width: 0;
      padding: 9px 4px;
      border-radius: 24px;
      border: 2px solid transparent;
      background: var(--secondary-background-color, rgba(127, 127, 127, 0.2));
      font-weight: 700;
      text-align: center;
    }
    .chip.on {
      color: var(--primary-color);
      background-image: linear-gradient(rgba(var(--rgb-primary-color, 3, 169, 244), 0.14), rgba(var(--rgb-primary-color, 3, 169, 244), 0.14));
    }
    .btns {
      display: flex;
      gap: 12px;
      margin-top: 20px;
    }
    .btns button {
      flex: 1;
      padding: 11px;
      border-radius: 24px;
      font-weight: 700;
      color: var(--primary-color);
      background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.14);
    }
  `);var Zt={ATTRIBUTE:1,CHILD:2,PROPERTY:3,BOOLEAN_ATTRIBUTE:4,EVENT:5,ELEMENT:6},at=i=>(...t)=>({_$litDirective$:i,values:t}),nt=class{constructor(t){}get _$AU(){return this._$AM._$AU}_$AT(t,e,s){this._$Ct=t,this._$AM=e,this._$Ci=s}_$AS(t,e){return this.update(t,e)}update(t,e){return this.render(...e)}};var V=class extends nt{constructor(t){if(super(t),this.it=h,t.type!==Zt.CHILD)throw Error(this.constructor.directiveName+"() can only be used in child bindings")}render(t){if(t===h||t==null)return this._t=void 0,this.it=t;if(t===E)return t;if(typeof t!="string")throw Error(this.constructor.directiveName+"() called with a non-string value");if(t===this.it)return this._t;this.it=t;let e=[t];return e.raw=e,this._t={_$litType$:this.constructor.resultType,strings:e,values:[]}}};V.directiveName="unsafeHTML",V.resultType=1;var to=at(V);var Tt=class extends V{};Tt.directiveName="unsafeSVG",Tt.resultType=2;var b=at(Tt);var Ps=2e3,Ns=[1,2,3].map(i=>`<circle class="track" r="${(y[i]+y[i+1])/2}" stroke-width="${Gt}"/>`).join(""),Is=[2,3].map(i=>`<circle class="sep" r="${y[i]}"/>`).join(""),Hs=(()=>{let i="";for(let t=0;t<24;t++){let[e,s]=$(y[1],t*15),[o,r]=$(y[4],t*15);i+=`<line x1="${e.toFixed(2)}" y1="${s.toFixed(2)}" x2="${o.toFixed(2)}" y2="${r.toFixed(2)}"/>`}return i})(),js=(()=>{let i="";for(let t of[y[2],y[3]])for(let e=0;e<24;e++){let[s,o]=$(t,e*15);i+=`<circle cx="${s.toFixed(2)}" cy="${o.toFixed(2)}" r="${es}"/>`}return i})(),lt=class extends g{constructor(){super(),this.profile="",this.stepMinutes=60,this.highlightHour=-1,this._spokes=!1,this._drag=null}disconnectedCallback(){super.disconnectedCallback(),clearTimeout(this._spokesTimer)}_runs(){let t=this.stepMinutes/15,e=[...this.profile||"1".repeat(96)];if(this._drag)for(let[s,o]of this._drag.cells)for(let r=0;r<t;r++)e[s+r]=tt[o];return os(e)}_cellsSvg(t){let e="";for(let s of t){if(s.full){e+=`<circle class="full full${s.lvl}" r="${(y[s.lvl]+y[s.lvl+1])/2}" stroke-width="${Gt}"/>`;continue}let o=Ot(y[s.lvl],y[s.lvl+1],s.start*U,(s.start+s.len)*U);e+=`<path class="run${s.lvl}" d="${o}"/>`}return e}_darkSvg(t){let e=this.highlightHour;if(!(e>=0&&e<24))return"";let s="";for(let o of t)o.full?s+=`<circle r="${(y[o.lvl]+y[o.lvl+1])/2}" stroke-width="${Gt}"/>`:s+=`<path d="${Ot(y[o.lvl],y[o.lvl+1],o.start*U,(o.start+o.len)*U)}"/>`;return`<defs><clipPath id="nowclip"><path d="${D(y[1],y[4],e*15,(e+1)*15)}"/></clipPath></defs><g class="dk" clip-path="url(#nowclip)">${s}</g>`}_tlabelsSvg(){return[1,2,3].map(t=>`<text x="0" y="${(-(y[t]+y[t+1])/2).toFixed(2)}">T${t}</text>`).join("")}_previewSvg(){if(!this._drag)return"";let t=this.stepMinutes/15,e="";for(let[s,o]of this._drag.cells)e+=`<path class="hl-light" d="${D(y[o],y[o+1],s*U,(s+t)*U)}"/>`;return e}_nowSvg(){let t=this.highlightHour;return t>=0&&t<24?`<path class="now" d="${D(y[1],y[4],t*15,(t+1)*15)}"/>`:""}_pos(t){let e=this.renderRoot.querySelector(".ringsvg").getBoundingClientRect(),s=1080/e.width,o=(t.clientX-e.left)*s-540,r=(t.clientY-e.top)*s-540,n=Math.atan2(o,-r)*180/Math.PI;return n<0&&(n+=360),{r:Math.hypot(o,r),a:n}}_onDown(t){if(this.locked)return;let e=this._pos(t);if(!(e.r<y[1]||e.r>y[4]+25)){t.preventDefault();try{t.currentTarget.setPointerCapture(t.pointerId)}catch{}this._drag={cells:new Map,id:t.pointerId},clearTimeout(this._spokesTimer),this._spokes=!0,this._paint(e)}}_onMove(t){if(!this._drag||t.pointerId!==this._drag.id)return;let e=this._pos(t);e.r<y[1]||this._paint(e)}_paint(t){let e=t.r<y[2]?1:t.r<y[3]?2:3,s=this.stepMinutes/15,o=Math.min(Math.floor(t.a*4/this.stepMinutes)*s,96-s);this._drag.cells.get(o)!==e&&(this._drag.cells.set(o,e),this.requestUpdate())}_onUp(t){let e=this._drag;if(!e||t.pointerId!==e.id)return;this._drag=null,clearTimeout(this._spokesTimer),this._spokesTimer=setTimeout(()=>this._spokes=!1,Ps);try{t.currentTarget.releasePointerCapture(t.pointerId)}catch{}if(!this.profile||!e.cells.size)return;let s=this.stepMinutes/15,o=[...this.profile];for(let[n,l]of e.cells)for(let a=0;a<s;a++)o[n+a]=tt[l];let r=o.join("");r!==this.profile&&this.dispatchEvent(new CustomEvent("profile-change",{detail:{profile:r}}))}_fire(t,e){this.dispatchEvent(new CustomEvent(t,{detail:e}))}render(){let t=this._runs();return c`
      <svg
        class="ringsvg"
        viewBox="-540 -540 1080 1080"
        @pointerdown=${this._onDown}
        @pointermove=${this._onMove}
        @pointerup=${this._onUp}
        @pointercancel=${this._onUp}
      >
        <circle class="hit" r=${y[4]+25}></circle>
        <g class="tracks">${b(Ns)}</g>
        ${b(this._nowSvg())}
        <g class="cells">${b(this._cellsSvg(t))}</g>
        ${b(this._darkSvg(t))}
        <g class="seps">${b(Is)}</g>
        <g class="spokes ${this._spokes?"on":""}">${b(Hs)}</g>
        <g class="dots">${b(js)}</g>
        ${b(this._previewSvg())}
        <g class="tl">${b(this._tlabelsSvg())}</g>
        <g class="labels">${b(is)}</g>
      </svg>
      ${this.warning?c`<div class="warn">${this.warning}</div>`:h}
      <div class="center">
        <button class="daybtn" @click=${()=>this._fire("day-open")}>
          <span class="daylbl">${this.dayLabel}</span>
        </button>
      </div>
    `}};m(lt,"properties",{profile:{type:String},stepMinutes:{type:Number,attribute:"step-minutes"},dayLabel:{type:String,attribute:"day-label"},season:{type:String,reflect:!0},warning:{type:String},locked:{type:Boolean},highlightHour:{type:Number,attribute:"highlight-hour"},_drag:{state:!0},_spokes:{state:!0}}),m(lt,"styles",[Q,_`
    :host {
      display: block;
      position: relative;
      width: var(--dial-size, 100%);
      height: var(--dial-size, 100%);
      color: var(--primary-text-color);
      font-family: inherit;
      user-select: none;
      -webkit-user-select: none;
      -webkit-touch-callout: none;
      --u: calc(var(--dial-size, 1080px) / 1080);
    }
    svg {
      display: block;
    }
    button {
      font: inherit;
      color: inherit;
      background: none;
      border: 0;
      padding: 0;
      cursor: pointer;
      -webkit-tap-highlight-color: transparent;
    }
    .ringsvg {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      touch-action: none;
      font-family: inherit;
      pointer-events: none;
    }
    .hit {
      fill: transparent;
      pointer-events: all;
    }
    .track {
      fill: none;
      stroke: var(--disabled-color, #888);
      stroke-opacity: 0.3;
    }
    .sep {
      fill: none;
      stroke: var(--card-background-color, #1c1c1c);
      stroke-width: 3;
    }
    .spokes {
      opacity: 0;
      transition: opacity 180ms ease-in-out;
    }
    .spokes.on {
      opacity: 1;
    }
    .spokes line {
      stroke: var(--card-background-color, #1c1c1c);
      stroke-width: 3;
    }
    .run1 {
      fill: var(--lvl1);
    }
    .run2 {
      fill: var(--lvl2);
    }
    .run3 {
      fill: var(--lvl3);
    }
    .full {
      fill: none;
    }
    .full1 {
      stroke: var(--lvl1);
    }
    .full2 {
      stroke: var(--lvl2);
    }
    .full3 {
      stroke: var(--lvl3);
    }
    .now {
      fill: var(--primary-text-color);
      fill-opacity: 0.12;
      stroke: none;
    }
    .hl-light {
      fill: var(--primary-text-color);
      fill-opacity: 0.18;
    }
    /* Ora attuale: le barre colorate di quell'ora vengono scurite un poco. */
    .dk path {
      fill: #000;
      fill-opacity: 0.16;
    }
    .dk circle {
      fill: none;
      stroke: #000;
      stroke-opacity: 0.16;
    }
    .dots circle {
      fill: var(--primary-text-color);
      fill-opacity: 0.5;
    }
    .tl text {
      font-size: 34px;
      font-weight: 700;
      text-anchor: middle;
      dominant-baseline: central;
    }
    .tl text {
      fill: var(--primary-text-color);
    }
    .labels text {
      fill: var(--secondary-text-color);
      font-size: 31px;
      font-weight: 600;
      text-anchor: middle;
      dominant-baseline: central;
    }
    .warn {
      position: absolute;
      left: 0;
      right: 0;
      top: 50%;
      transform: translateY(calc(var(--u) * 150));
      text-align: center;
      font-size: calc(var(--u) * 30);
      color: var(--warning-color, #ffb74d);
      padding: 0 calc(var(--u) * 200);
      pointer-events: none;
    }
    .center {
      position: absolute;
      left: 50%;
      top: 50%;
      transform: translate(-50%, -50%);
      width: calc(var(--u) * 400);
      text-align: center;
      display: flex;
      justify-content: center;
      pointer-events: none;
    }
    .center > * {
      pointer-events: auto;
    }
    .daybtn {
      padding: calc(var(--u) * 10) calc(var(--u) * 30);
      border-radius: 12px;
      position: relative;
      overflow: hidden;
    }
    .daybtn::before {
      content: "";
      position: absolute;
      inset: 0;
      background: var(--disabled-color, rgba(127, 127, 127, 0.5));
      opacity: 0.2;
      transition: opacity 180ms ease-in-out;
    }
    .daybtn:hover::before {
      opacity: 0.28;
    }
    .daylbl {
      position: relative;
      display: block;
      font-size: calc(var(--u) * 60);
      font-weight: 800;
      line-height: calc(var(--u) * 80);
      white-space: nowrap;
    }
  `]);var Us=1080,Xt=994,Mt=360,Ds=(Xt-Mt)/3,w=30,R=4,B=w*2/R,A=i=>Mt+Ds*i,C=i=>i.toFixed(2),kt=i=>String(i).padStart(2,"0"),Vs=(i,t,e)=>{let[s,o]=$(i,t),[r,n]=$(i,e);return`M${C(s)} ${C(o)}A${i} ${i} 0 0 1 ${C(r)} ${C(n)}`},Bs=[1,2,3].map(i=>`<path class="track" d="${D(A(i-1),A(i),-w,w)}"/>`).join(""),qs=[1,2].map(i=>`<path d="${Vs(A(i),-w,w)}"/>`).join(""),Js=(()=>{let i="";for(let t=1;t<R;t++){let e=-w+t*B,[s,o]=$(Mt,e),[r,n]=$(Xt,e);i+=`<line x1="${C(s)}" y1="${C(o)}" x2="${C(r)}" y2="${C(n)}"/>`}return i})(),ct=class extends g{constructor(){super(),this.profile="",this.hour=0,this._drag=null}_qOf(t){return this.hour*4+t}_cellsSvg(){let t=[...this.profile||"1".repeat(96)],e="";if(this._drag)for(let[n,l]of this._drag.cells){t[n]=tt[l];let a=-w+(n-this.hour*4)*B;e+=`<path class="hl-light" d="${D(A(l-1),A(l),a,a+B)}"/>`}let s=t.map(_e),o=this.hour*4,r="";for(let n=1;n<=3;n++){let l=0;for(;l<R;){if(s[o+l]!==n){l++;continue}let a=l;for(;a+1<R&&s[o+a+1]===n;)a++;let p=l===0&&s[(o-1+96)%96]===n,d=a===R-1&&s[(o+R)%96]===n,u=Ot(A(n-1),A(n),-w+l*B,-w+(a+1)*B,!p,!d);r+=`<path class="run${n}" d="${u}"/>`,l=a+1}}return r+e}_tlabelsSvg(){return[1,2,3].map(t=>`<text x="0" y="${C(-(A(t-1)+A(t))/2)}">T${t}</text>`).join("")}_timesSvg(){let t="";for(let e=0;e<=R;e++){let s=-w+e*B,[o,r]=$((Xt+Us)/2,s),n=this.hour*60+e*15,l=e===0?"start":e===R?"end":"middle";t+=`<text x="${C(o)}" y="${C(r)}" text-anchor="${l}">${kt(Math.floor(n/60)%24)}:${kt(n%60)}</text>`}return t}_pos(t){let e=this.renderRoot.querySelector("svg").getBoundingClientRect(),s=1080/e.width,o=(t.clientX-e.left)*s-540,r=(t.clientY-e.top)*s-1080;return{r:Math.hypot(o,r),a:Math.atan2(o,-r)*180/Math.PI}}_onDown(t){let e=this._pos(t);if(!(e.r<Mt||e.r>Xt+20||Math.abs(e.a)>w)){t.preventDefault();try{t.currentTarget.setPointerCapture(t.pointerId)}catch{}this._drag={cells:new Map,id:t.pointerId},this._paint(e)}}_onMove(t){if(!this._drag||t.pointerId!==this._drag.id)return;let e=this._pos(t);e.r<Mt||this._paint(e)}_paint(t){let e=t.r<A(1)?1:t.r<A(2)?2:3,s=Math.max(-w,Math.min(w-.001,t.a)),o=Math.floor((s+w)/B),r=this._qOf(o);this._drag.cells.get(r)!==e&&(this._drag.cells.set(r,e),this.requestUpdate())}_onUp(t){let e=this._drag;if(!e||t.pointerId!==e.id)return;this._drag=null;try{t.currentTarget.releasePointerCapture(t.pointerId)}catch{}if(!this.profile||!e.cells.size)return;let s=[...this.profile];for(let[r,n]of e.cells)s[r]=tt[n];let o=s.join("");o!==this.profile&&this.dispatchEvent(new CustomEvent("profile-change",{detail:{profile:o}}))}_setHour(t){let e=(Math.round(t)%24+24)%24;this.dispatchEvent(new CustomEvent("hour-change",{detail:{hour:e}}))}_typed(t){let e=parseInt(t.target.value,10);if(Number.isNaN(e)){t.target.value=kt(this.hour);return}this._setHour(Math.min(23,Math.max(0,e))),t.target.value=kt(Math.min(23,Math.max(0,e)))}render(){return c`
      <svg
        viewBox="-540 -1080 1080 1080"
        @pointerdown=${this._onDown}
        @pointermove=${this._onMove}
        @pointerup=${this._onUp}
        @pointercancel=${this._onUp}
      >
        <g class="tracks">${b(Bs)}</g>
        <g class="cells">${b(this._cellsSvg())}</g>
        <g class="seps">${b(qs)}</g>
        <g class="spokes">${b(Js)}</g>
        <g class="tl">${b(this._tlabelsSvg())}</g>
        <g class="times">${b(this._timesSvg())}</g>
        <text class="day" x="0" y="-262">${this.dayLabel}</text>
      </svg>
      <div class="controls">
        <button aria-label="-" @click=${()=>this._setHour(this.hour-1)}>
          <ha-icon icon="mdi:minus"></ha-icon>
        </button>
        <input
          type="text"
          inputmode="numeric"
          maxlength="2"
          aria-label=${this.hourLabel}
          .value=${kt(this.hour)}
          @focus=${t=>t.target.select()}
          @change=${this._typed}
          @keydown=${t=>t.key==="Enter"&&t.target.blur()}
        />
        <button aria-label="+" @click=${()=>this._setHour(this.hour+1)}>
          <ha-icon icon="mdi:plus"></ha-icon>
        </button>
      </div>
    `}};m(ct,"properties",{profile:{type:String},hour:{type:Number},dayLabel:{type:String,attribute:"day-label"},hourLabel:{type:String,attribute:"hour-label"},season:{type:String,reflect:!0},_drag:{state:!0}}),m(ct,"styles",[Q,_`
    :host {
      display: block;
      position: relative;
      width: var(--dial-size, 100%);
      height: var(--dial-size, 100%);
      color: var(--primary-text-color);
      font-family: inherit;
      user-select: none;
      -webkit-user-select: none;
      -webkit-touch-callout: none;
      --u: calc(var(--dial-size, 1080px) / 1080);
    }
    svg {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      touch-action: none;
      font-family: inherit;
    }
    .track {
      fill: var(--disabled-color, #888);
      fill-opacity: 0.3;
    }
    .seps path,
    .spokes line {
      fill: none;
      stroke: var(--card-background-color, #1c1c1c);
      stroke-width: 3;
    }
    .run1 {
      fill: var(--lvl1);
    }
    .run2 {
      fill: var(--lvl2);
    }
    .run3 {
      fill: var(--lvl3);
    }
    .hl-light {
      fill: var(--primary-text-color);
      fill-opacity: 0.18;
    }
    .tl text {
      font-size: 100px;
      font-weight: 700;
      text-anchor: middle;
      dominant-baseline: central;
    }
    .tl text {
      fill: var(--primary-text-color);
    }
    .times text {
      fill: var(--secondary-text-color);
      font-size: 31px;
      font-weight: 600;
      dominant-baseline: central;
    }
    .day {
      fill: var(--primary-text-color);
      font-size: 64px;
      font-weight: 800;
      text-anchor: middle;
      dominant-baseline: central;
    }
    .controls {
      position: absolute;
      left: 50%;
      bottom: calc(var(--u) * 20);
      transform: translateX(-50%);
      display: flex;
      align-items: center;
      gap: calc(var(--u) * 28);
    }
    button {
      font: inherit;
      color: var(--secondary-text-color);
      background: none;
      cursor: pointer;
      width: calc(var(--u) * 150);
      height: calc(var(--u) * 150);
      border-radius: 50%;
      border: 1px solid var(--secondary-text-color);
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0;
      -webkit-tap-highlight-color: transparent;
    }
    button ha-icon {
      --mdc-icon-size: calc(var(--u) * 80);
      display: flex;
    }
    input {
      font: inherit;
      font-size: calc(var(--u) * 100);
      font-weight: 600;
      width: calc(var(--u) * 190);
      height: calc(var(--u) * 150);
      box-sizing: border-box;
      text-align: center;
      color: var(--primary-text-color);
      background: none;
      border: 1px solid var(--divider-color, var(--secondary-text-color));
      border-radius: calc(var(--u) * 28);
      padding: 0;
      outline: none;
    }
    input:focus {
      border-color: var(--primary-color);
    }
  `]);var q=["t1","t2","t3"],ve={min:5,max:35,step:.1};function rs(i,t){let e=i?.entities?.[t]?.device_id;if(!e)return null;let s={};for(let[o,r]of Object.entries(i.entities)){if(!o.startsWith("number.")||r.device_id!==e)continue;let n=String(i.states[o]?.attributes?.friendly_name||"").trim().toLowerCase(),l=o.split(".")[1];for(let a of q)(n===a||n.endsWith(` ${a}`)||l.endsWith(`_${a}`))&&(s[a]=o)}return q.every(o=>s[o])?s:null}function Qt(i,t){let e={};for(let s of q){let o=i.states[t[s]],r=o?parseFloat(o.state):NaN;e[s]=Number.isNaN(r)?null:r}return e}function ns(i,t){let e=i.states[t]?.attributes||{};return{min:Number(e.min??ve.min),max:Number(e.max??ve.max),step:Number(e.step??ve.step)}}var Lt=i=>Math.round(i*10)/10;function as(i,t,e,s){let{t1:o,t2:r,t3:n}=e,{min:l,max:a,step:p}=s,d=Lt(Math.round(t/p)*p);return i==="t1"&&r!=null&&d>=r?d=Lt(r-p):i==="t2"?o!=null&&d<=o?d=Lt(o+p):n!=null&&d>=n&&(d=Lt(n-p)):i==="t3"&&r!=null&&d<=r&&(d=Lt(r+p)),Math.max(l,Math.min(a,d))}function ls(i,t){let e=["t3","t2","t1"].filter(o=>o in i&&i[o]>(t[o]??-1/0)),s=["t1","t2","t3"].filter(o=>o in i&&!e.includes(o));return[...e,...s]}var cs=.5,Fs=c`<svg viewBox="0 0 24 24"><path d="M19,13H5V11H19V13Z" /></svg>`,Ys=c`<svg viewBox="0 0 24 24"><path d="M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z" /></svg>`,ht=class extends g{_fmt(t){return t==null?"--":Number(t).toLocaleString(this.language||"it",{minimumFractionDigits:1,maximumFractionDigits:1})}_emit(t,e){Number.isNaN(e)||this.dispatchEvent(new CustomEvent("temp-change",{detail:{key:t,value:e}}))}_typed(t,e){let s=parseFloat(String(e.target.value).replace(",","."));e.target.value=this._fmt(this.values?.[t]),e.target.style.width=`${Math.max(2,e.target.value.length)}ch`,this._emit(t,s)}render(){return c`${q.map(t=>{let e=this.values?.[t];return c`<div class="cell">
        <span class="lbl">${t.toUpperCase()}</span>
        <div class="box">
        <button class="minus" aria-label="-" @click=${()=>e!=null&&this._emit(t,e-cs)}>
          ${Fs}
        </button>
        <span class="val">
          <input
            inputmode="decimal"
            aria-label=${t.toUpperCase()}
            .value=${this._fmt(e)}
            style="width:${Math.max(2,this._fmt(e).length)}ch"
            @input=${s=>s.target.style.width=`${Math.max(2,s.target.value.length)}ch`}
            @focus=${s=>s.target.select()}
            @change=${s=>this._typed(t,s)}
            @keydown=${s=>s.key==="Enter"&&s.target.blur()}
          /><span class="deg">°</span>
        </span>
        <button class="plus" aria-label="+" @click=${()=>e!=null&&this._emit(t,e+cs)}>
          ${Ys}
        </button>
        </div>
      </div>`})}`}};m(ht,"properties",{values:{attribute:!1},language:{type:String},disabled:{type:Boolean},season:{type:String,reflect:!0}}),m(ht,"styles",[Q,_`
    /* La fascia sopra il quadrante resta alta come prima (45 px): le barre, alte come i pulsanti
       sotto (--feature-height), partono dall'alto senza spostare nulla. */
    :host {
      display: flex;
      align-items: flex-start;
      justify-content: center;
      gap: 12px;
      width: 100%;
      height: 100%;
      box-sizing: border-box;
      padding: 0 16px;
      font-family: inherit;
      --mdc-icon-size: 16px;
    }
    /* Come ha-control-number-buttons: sfondo --disabled-color al 20%, − e + larghi 35 px ai lati. */
    /* Contenitore: tiene l'etichetta fuori dalla barra, nel margine sopra, senza spostare la barra. */
    .cell {
      position: relative;
      flex: 1 1 0;
      min-width: 0;
      max-width: 190px;
    }
    .box {
      position: relative;
      width: 100%;
      height: var(--feature-height, 48px);
      box-sizing: border-box;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: var(--feature-border-radius, 12px);
      overflow: hidden;
      color: var(--primary-text-color);
      font-weight: var(--ha-font-weight-medium, 500);
    }
    .box::before {
      content: "";
      position: absolute;
      inset: 0;
      background: var(--disabled-color, rgba(127, 127, 127, 0.5));
      opacity: 0.2;
    }
    .box:focus-within {
      box-shadow: 0 0 0 2px var(--secondary-text-color);
    }
    .lbl {
      position: absolute;
      bottom: 100%;
      margin-bottom: 3px;
      left: 0;
      width: 35px;
      text-align: center;
      font-size: 11px;
      font-weight: 700;
      line-height: 12px;
      color: var(--primary-text-color);
      pointer-events: none;
    }
    .val {
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: var(--ha-font-size-l, 16px);
    }
    button {
      position: absolute;
      top: 0;
      bottom: 0;
      width: 35px;
      padding: 0;
      border: 0;
      background: none;
      color: inherit;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      -webkit-tap-highlight-color: transparent;
    }
    button.minus {
      left: 0;
    }
    button.plus {
      right: 0;
    }
    button:active {
      background: rgba(127, 127, 127, 0.25);
    }
    button svg {
      width: 16px;
      height: 16px;
      fill: currentColor;
    }
    input {
      font: inherit;
      color: inherit;
      min-width: 0;
      text-align: center;
      background: none;
      border: 0;
      outline: none;
      padding: 0;
    }
    .deg {
      width: 0.5em;
    }
    :host([disabled]) {
      opacity: 0.5;
      pointer-events: none;
    }
  `]);var Ws=["auto","jolly","heat","cool"],Gs=i=>String(i).charAt(0).toUpperCase()+String(i).slice(1).replace(/_/g," "),Ks=.98125/.87519,dt=class extends g{constructor(){super(),this.stepMinutes=60,this._program=!1,this._zoom=!1,this._zoomHour=0,this._temps={},this._day=null,this._drafts={},this._copyOpen=!1,this._dayOpen=!1,this._saving=!1,this._resizeObserver=new ResizeObserver(()=>this._placeProgramDial())}get _stateObj(){return this.hass?.states[this.entityId]}firstUpdated(){this.renderRoot.querySelector("dialog").showModal(),this._resizeObserver.observe(this.renderRoot.querySelector("dialog"))}disconnectedCallback(){super.disconnectedCallback(),this._resizeObserver.disconnect()}updated(t){(t.has("_program")||t.has("_zoom")||t.has("hass")||t.has("_day"))&&this._placeProgramDial()}_placeProgramDial(){let t=this.renderRoot?.querySelector(".dial-area"),e=t?.querySelector(".control");if(!e)return;let s=this._stateObj,o=()=>Ft(e,!!s&&X(s));o(),e.updateComplete?.then(o),Yt(t,e,t.querySelector(".status"));let r=t.querySelector(".program");if(!r)return;let n=t.getBoundingClientRect(),l=e.getBoundingClientRect();r.style.left=`${l.left-n.left}px`,r.style.top=`${l.top-n.top}px`,r.style.width=`${l.width}px`,r.style.height=`${l.height}px`;let a=Math.max(0,Math.min(l.width,l.height)-16),p=r.firstElementChild,d=p?.localName==="domo-program-dial"?Ks:1;p?.style.setProperty("--dial-size",`${a*d}px`)}_close(){this.renderRoot.querySelector("dialog")?.close()}_onClosed(){this.dispatchEvent(new CustomEvent("closed"))}_backdrop(t){t.target===t.currentTarget&&this._close()}_native(t){this._close(),L(this,"hass-more-info",{entityId:this.entityId,...t?{view:t}:{}})}_deviceInfo(){let t=this.hass.entities?.[this.entityId]?.device_id;if(!t){this._native();return}this._close(),history.pushState(null,"",`/config/devices/device/${t}`),L(window,"location-changed",{replace:!1})}_toast(t){L(this,"hass-notification",{message:t&&t.message||String(t)})}_call(t,e,s){return this.hass.callService(t,e,s).catch(o=>this._toast(o))}_todayKey(){return Y[(new Date().getDay()+6)%7]}_openProgram(){let t=this._stateObj;this._day=t&&X(t)?"jolly":this._todayKey(),this._drafts={},this._copyOpen=!1,this._dayOpen=!1,this._zoom=!1,this._temps={},this._program=!0}_openZoom(){this._zoomHour=new Date().getHours(),this._zoom=!0}_tempEntities(){return rs(this.hass,this.entityId)}_tempValues(t){let e=Qt(this.hass,t),s={};return q.forEach(o=>{s[o]=this._temps[o]??e[o]}),s}_tempChanged(t){let e=this._tempEntities();if(!e)return;let{key:s,value:o}=t.detail,r=as(s,o,this._tempValues(e),ns(this.hass,e[s]));this._temps={...this._temps,[s]:r}}_profileOf(t){let e=this._drafts[t]??this._stateObj?.attributes.profile_by_day?.[t];return ss(e)?e:null}_applyCopy(t){let e=this._profileOf(this._day);if(this._copyOpen=!1,this._dayOpen=!1,!e)return;let s={...this._drafts};t.detail.forEach(o=>{s[o]=e}),this._drafts=s}_season(){return this._stateObj&&Qe(this._stateObj)?"summer":"winter"}_isDirty(){let t=this._stateObj?.attributes.profile_by_day||{};if(Object.entries(this._drafts).some(([o,r])=>r!==t[o]))return!0;let e=this._tempEntities();if(!e)return!1;let s=Qt(this.hass,e);return Object.entries(this._temps).some(([o,r])=>r!==s[o])}_closeProgram(){this._drafts={},this._temps={},this._copyOpen=!1,this._dayOpen=!1,this._zoom=!1,this._program=!1}async _save(){if(this._saving)return;this._saving=!0;let t=this._stateObj?.attributes.profile_by_day||{};for(let[s,o]of Object.entries(this._drafts)){if(o===t[s])continue;try{await this.hass.callService("domo","set_thermal_profile",{entity_id:this.entityId,day:s,profile:o})}catch(l){this._toast(l),this._saving=!1;return}let{[s]:r,...n}=this._drafts;this._drafts=n}this._drafts={};let e=this._tempEntities();if(e&&Object.keys(this._temps).length){let s=Qt(this.hass,e);for(let o of ls(this._temps,s))if(this._temps[o]!==s[o])try{await this.hass.callService("number","set_value",{entity_id:e[o],value:this._temps[o]})}catch(r){this._toast(r),this._saving=!1;return}}this._temps={},this._copyOpen=!1,this._dayOpen=!1,this._zoom=!1,this._program=!1,this._saving=!1}_areaName(){let t=this.hass,e=t.entities?.[this.entityId];if(!e)return null;let s=e.area_id||e.device_id&&t.devices?.[e.device_id]?.area_id;return s&&t.areas?.[s]?.name||null}_statsHtml(t){let e=t.attributes,s=this.hass.config?.unit_system?.temperature||"\xB0C",o=(l,a)=>Number(l).toLocaleString(this.hass.language||"it",{minimumFractionDigits:a,maximumFractionDigits:a}),r=e.current_temperature,n=e.current_humidity;return c`<div class="stats">
      <div>
        <div class="l">${this.hass.formatEntityAttributeName?.(t,"current_temperature")||f(this.hass,"curTemp")}</div>
        <div class="v">${r!=null?`${o(r,1)} ${s}`:"--"}</div>
      </div>
      ${n!=null?c`<div>
            <div class="l">${this.hass.formatEntityAttributeName?.(t,"current_humidity")||f(this.hass,"curHum")}</div>
            <div class="v">${Math.round(n)}%</div>
          </div>`:h}
    </div>`}_listSelect(t,e,s,o,r,n,l={}){let a=t.attributes[`${e}s`]||[];if(!a.length)return h;let p=a.map(d=>({value:d,label:e==="fan_mode"&&Xe(this.hass,d)||this.hass.formatEntityAttributeValue?.(t,e,d)||Gs(d),icon:o(d)}));return c`<domo-feature-select
      ?compact=${l.compact}
      ?icon-only=${l.iconOnly}
      .caption=${l.caption}
      .label=${this.hass.localize(r)}
      .options=${p}
      .value=${t.attributes[e]}
      ?disabled=${t.state==="unavailable"}
      @selected=${d=>this._call("climate",s,{entity_id:this.entityId,[n]:d.detail.value})}
    ></domo-feature-select>`}_programDial(){let t=this._profileOf(this._day),e=s=>{this._drafts={...this._drafts,[this._day]:s.detail.profile}};return this._zoom?c`<div class="program">
        <domo-hour-zoom
          season=${this._season()}
          .profile=${t||""}
          .hour=${this._zoomHour}
          day-label=${f(this.hass,this._day)}
          hour-label=${f(this.hass,"hour")}
          @profile-change=${e}
          @hour-change=${s=>{this._zoomHour=s.detail.hour}}
        ></domo-hour-zoom>
      </div>`:c`<div class="program">
      <domo-program-dial
        season=${this._season()}
        .profile=${t||""}
        .highlightHour=${this._day===this._todayKey()?new Date().getHours():-1}
        step-minutes=${this.stepMinutes}
        day-label=${f(this.hass,this._day)}
        .warning=${t?"":f(this.hass,"missing")}
        ?locked=${!t}
        @profile-change=${s=>{this._drafts={...this._drafts,[this._day]:s.detail.profile}}}
        @day-open=${()=>{this._dayOpen=!0}}
      ></domo-program-dial>
    </div>`}render(){let t=this._stateObj;if(!this.hass||!t)return c`<dialog @close=${this._onClosed}></dialog>`;let e=ot(t),s=this._areaName(),o=Z(this.hass,t,void 0);return c`
      <dialog @close=${this._onClosed} @click=${this._backdrop}>
        <div class="surface">
          <div class="header">
            <ha-icon-button class="close" .label=${f(this.hass,"close")} @click=${this._close}>
              <ha-icon icon="mdi:close"></ha-icon>
            </ha-icon-button>
            <div class="titles">
              ${s?c`<div class="area">${s}</div>`:h}
              <div class="name">${o}</div>
            </div>
            <ha-icon-button .label=${f(this.hass,"history")} @click=${()=>this._native("history")}>
              <ha-icon icon="mdi:chart-box-outline"></ha-icon>
            </ha-icon-button>
            <ha-icon-button .label=${f(this.hass,"settings")} @click=${()=>this._native("settings")}>
              <ha-icon icon="mdi:cog-outline"></ha-icon>
            </ha-icon-button>
            <ha-icon-button .label=${f(this.hass,"more")} @click=${this._deviceInfo}>
              <ha-icon icon="mdi:dots-vertical"></ha-icon>
            </ha-icon-button>
          </div>

          <div class="top">
            ${this._program&&this._tempEntities()?c`<domo-temp-fields
                  season=${this._season()}
                  .language=${this.hass.language}
                  .values=${this._tempValues(this._tempEntities())}
                  ?disabled=${this._saving}
                  @temp-change=${this._tempChanged}
                ></domo-temp-fields>`:this._statsHtml(t)}
          </div>

          <div class="dial-area">
            <ha-state-control-climate-temperature
              class="control ${this._program?"hidden":""}"
              prevent-interaction-on-scroll
              .hass=${this.hass}
              .stateObj=${t}
            ></ha-state-control-climate-temperature>
            ${this._program?this._programDial():c`<domo-status-icons
                  class="floating status"
                  ?window-open=${e.windowOpen}
                  ?absent=${e.absent}
                ></domo-status-icons>`}
          </div>

          <div class="chips-area ${this._program?"program":""}">
            <div class="chips">
              <domo-feature-select
                compact
                .label=${this.hass.localize("ui.card.climate.operation")}
                .options=${ts(this.hass,t,void 0,!0)}
                .value=${Ct(t)}
                ?disabled=${t.state==="unavailable"}
                @selected=${r=>this._call(...Wt(this.entityId,r.detail.value))}
              ></domo-feature-select>
              <domo-feature-button
                center
                icon="mdi:clock-outline"
                .lines=${[f(this.hass,"program")]}
                @click=${this._openProgram}
              ></domo-feature-button>
              ${Ws.includes(Ct(t))?this._listSelect(t,"fan_mode","set_fan_mode",r=>Ce[r]||"mdi:fan","ui.card.climate.fan_mode","fan_mode",{compact:!0,caption:f(this.hass,"fan")}):h}
              ${this._listSelect(t,"swing_mode","set_swing_mode",()=>"mdi:arrow-oscillating","ui.card.climate.swing_mode","swing_mode",{compact:!0})}
            </div>
            ${this._program?c`<div class="save-slot">
                  ${this._zoom?c`<domo-feature-button
                        class="lens"
                        center
                        icon="mdi:magnify-minus-outline"
                        aria-label=${f(this.hass,"close")}
                        .lines=${[]}
                        @click=${()=>{this._zoom=!1}}
                      ></domo-feature-button>`:c`<domo-feature-button
                          class="lens"
                          center
                          icon="mdi:magnify-plus-outline"
                          aria-label=${f(this.hass,"zoomIn")}
                          .lines=${[]}
                          @click=${this._openZoom}
                        ></domo-feature-button>
                        <domo-feature-button
                          class="lens"
                          center
                          icon="mdi:content-copy"
                          aria-label=${f(this.hass,"copy")}
                          ?disabled=${!this._profileOf(this._day)}
                          .lines=${[]}
                          @click=${()=>{this._copyOpen=!0}}
                        ></domo-feature-button>
                        ${this._isDirty()?c`<domo-feature-button
                                class="lens"
                                center
                                icon="mdi:check"
                                aria-label=${f(this.hass,"saveClose")}
                                .lines=${[]}
                                @click=${this._save}
                              ></domo-feature-button>
                              <domo-feature-button
                                class="lens"
                                center
                                icon="mdi:close"
                                aria-label=${f(this.hass,"closeNoSave")}
                                .lines=${[]}
                                @click=${this._closeProgram}
                              ></domo-feature-button>`:c`<domo-feature-button
                              class="lens"
                              center
                              icon="mdi:close"
                              aria-label=${f(this.hass,"close")}
                              .lines=${[]}
                              @click=${this._closeProgram}
                            ></domo-feature-button>`}`}
                </div>`:h}
          </div>

          ${this._program&&!this._zoom&&this._dayOpen?c`<domo-day-dialog
                .hass=${this.hass}
                .day=${this._day}
                @cancel=${()=>this._dayOpen=!1}
                @select=${r=>{this._day=r.detail,this._dayOpen=!1}}
              ></domo-day-dialog>`:h}
          ${this._program&&!this._zoom&&this._copyOpen?c`<domo-copy-dialog
                .hass=${this.hass}
                .day=${this._day}
                @cancel=${()=>this._copyOpen=!1}
                @apply=${this._applyCopy}
              ></domo-copy-dialog>`:h}
        </div>
      </dialog>
    `}};m(dt,"properties",{hass:{attribute:!1},entityId:{type:String,attribute:"entity-id"},stepMinutes:{type:Number,attribute:"step-minutes"},_program:{state:!0},_zoom:{state:!0},_zoomHour:{state:!0},_temps:{state:!0},_day:{state:!0},_drafts:{state:!0},_copyOpen:{state:!0},_dayOpen:{state:!0},_saving:{state:!0}}),m(dt,"styles",_`
    :host {
      display: contents;
      --feature-height: 48px;
      --feature-border-radius: 12px;
    }
    dialog {
      width: min(580px, 100vw);
      max-width: 100vw;
      max-height: 100vh;
      margin: auto;
      padding: 0;
      border: 0;
      overflow: auto;
      color: var(--primary-text-color);
      background: var(--ha-dialog-surface-background, var(--mdc-theme-surface, var(--card-background-color, #fff)));
      border-radius: var(--ha-dialog-border-radius, 28px);
      box-shadow: var(--ha-dialog-box-shadow, 0 8px 32px rgba(0, 0, 0, 0.4));
      font-family: var(--ha-font-family-body, Roboto, Noto, sans-serif);
    }
    dialog::backdrop {
      background: var(--ha-dialog-scrim-color, rgba(0, 0, 0, 0.32));
      backdrop-filter: var(--dialog-backdrop-filter, none);
    }
    .surface {
      position: relative;
      display: flex;
      flex-direction: column;
      border-radius: inherit;
      overflow: hidden;
    }
    .header {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 12px 12px 0 12px;
      min-height: 64px;
      box-sizing: border-box;
    }
    .titles {
      flex: 1;
      min-width: 0;
      margin-inline-start: 12px;
      line-height: 1.2;
    }
    .area {
      font-size: var(--ha-font-size-m, 14px);
      color: var(--secondary-text-color);
    }
    .name {
      font-size: var(--ha-font-size-xl, 20px);
      font-weight: var(--ha-font-weight-medium, 500);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    ha-icon-button {
      --mdc-icon-button-size: 48px;
      color: var(--secondary-text-color);
    }
    ha-icon-button.close {
      color: var(--primary-text-color);
    }
    .top {
      display: flex;
      align-items: center;
      justify-content: center;
      margin-top: 24px;
      height: calc((var(--ha-font-size-l, 16px) + var(--ha-font-size-xl, 20px)) * 1.25);
    }
    .stats {
      display: flex;
      justify-content: center;
      gap: 48px;
      text-align: center;
      line-height: 1.25;
    }
    .stats .l {
      font-size: var(--ha-font-size-l, 16px);
      color: var(--secondary-text-color);
    }
    .stats .v {
      font-size: var(--ha-font-size-xl, 20px);
      font-weight: var(--ha-font-weight-medium, 500);
    }
    .dial-area {
      position: relative;
      display: flex;
      justify-content: center;
      margin-top: 8px;
    }
    .control {
      display: block;
      width: 100%;
      max-width: 344px;
      padding: 8px;
      box-sizing: border-box;
    }
    .control.hidden {
      visibility: hidden;
    }
    .dial-area > .program {
      position: absolute;
      display: flex;
      align-items: center;
      justify-content: center;
      box-sizing: border-box;
    }
    /* Il quadrante può essere più grande del riquadro: niente restringimento automatico. */
    .dial-area > .program > * {
      flex: none;
    }
    .chips-area {
      position: relative;
      padding: 8px 24px 24px 24px;
    }
    .chips {
      display: grid;
      grid-auto-flow: column;
      grid-auto-columns: 1fr;
      justify-content: center;
      gap: 12px;
      width: max-content;
      max-width: 100%;
      margin: 0 auto;
    }
    .chips > * {
      width: auto;
      min-width: 0;
    }
    .dial-area > .status {
      position: absolute;
      padding: 0;
    }
    .chips-area.program .chips {
      visibility: hidden;
    }
    .save-slot {
      position: absolute;
      inset: 8px 24px 24px 24px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .save-slot {
      gap: 12px;
    }
    .save-slot domo-feature-button.lens {
      width: var(--feature-height, 48px);
      min-width: var(--feature-height, 48px);
    }
  `);var J=class extends g{constructor(){super(...arguments);m(this,"_computeLabel",e=>e.name==="show_current_as_primary"?this.hass.localize("ui.panel.lovelace.editor.card.thermostat.show_current_as_primary"):e.name==="show_jolly"?f(this.hass,"showJolly"):this.hass.localize(`ui.panel.lovelace.editor.card.generic.${e.name}`)||e.name)}get schema(){return[{name:"entity",required:!0,selector:{entity:{domain:zt}}},{name:"name",selector:{text:{}}},{name:"theme",selector:{theme:{}}},{name:"show_current_as_primary",selector:{boolean:{}}}]}setConfig(e){this._config=e}_valueChanged(e){L(this,"config-changed",{config:e.detail.value})}render(){return!this.hass||!this._config?h:c`
      <ha-form
        .hass=${this.hass}
        .data=${this._config}
        .schema=${this.schema}
        .computeLabel=${this._computeLabel}
        @value-changed=${this._valueChanged}
      ></ha-form>
    `}};m(J,"properties",{hass:{attribute:!1},_config:{state:!0}});var te=class extends J{get schema(){return[{name:"entity",required:!0,selector:{entity:{domain:["climate"]}}},{name:"name",selector:{text:{}}},{name:"theme",selector:{theme:{}}},{name:"show_jolly",selector:{boolean:{}}}]}setConfig(t){super.setConfig({show_jolly:!0,...t})}};var Zs=["off","fan_only","dry","cool","heat","heat_cool","auto"],Xs={auto:"var(--state-climate-auto-color, #4caf50)",heat_cool:"var(--state-climate-heat_cool-color, #4caf50)",heat:"var(--state-climate-heat-color, #ff8100)",cool:"var(--state-climate-cool-color, #2b9af9)",dry:"var(--state-climate-dry-color, #efbd07)",fan_only:"var(--state-climate-fan_only-color, #8ac24a)",off:"var(--state-climate-off-color, var(--state-inactive-color, #9e9e9e))"},hs=i=>i==="jolly"?N:Xs[i]||"var(--state-climate-active-color, var(--state-active-color))",Qs=i=>i.state==="unavailable"||i.state==="unknown",pt=class extends g{constructor(){super(),this._dialogOpen=!1}static getConfigElement(){return document.createElement(jt)}static getStubConfig(t,e,s){let r=[...e||[],...s||[]].find(n=>n.startsWith("climate."))||Object.keys(t?.states||{}).find(n=>n.startsWith("climate."));return{type:`custom:${gt}`,entity:r||""}}setConfig(t){if(!t||!t.entity||!t.entity.startsWith("climate."))throw new Error("Specify an entity from within the climate domain");let e=Number(t.step_minutes);this._config={...t,show_jolly:t.show_jolly!==!1,step_minutes:Nt.includes(e)?e:It}}getCardSize(){return 2}getGridOptions(){return{columns:6,rows:2,min_columns:3,min_rows:2}}connectedCallback(){super.connectedCallback(),this._config&&At(this._config.entity)}disconnectedCallback(){super.disconnectedCallback(),this._dialogOpen=!1}updated(t){if(!(!this._config||!this.hass)&&(t.has("hass")||t.has("_config"))){let e=t.get("hass"),s=t.get("_config");(!e||!s||e.themes!==this.hass.themes||s.theme!==this._config.theme)&&Jt(this,this.hass.themes,this._config.theme)}}_modes(t){let e=o=>{let r=Zs.indexOf(o);return r===-1?-1:r},s=[...t.attributes.hvac_modes||[]].sort((o,r)=>e(o)-e(r));return this._config.show_jolly&&ge(t)&&s.push("jolly"),s}_pick(t){this.hass.callService(...Wt(this._config.entity,t)).catch(e=>{this.dispatchEvent(new CustomEvent("hass-notification",{detail:{message:e&&e.message||String(e)},bubbles:!0,composed:!0}))})}_secondary(t){let e=this.hass,o=(t.attributes.hvac_action?e.formatEntityAttributeValue?.(t,"hvac_action"):null)||e.formatEntityState?.(t)||t.state,r=t.attributes.current_temperature!=null?e.formatEntityAttributeValue?.(t,"current_temperature"):null;return[o,r].filter(Boolean).join(" \xB7 ")}render(){if(!this.hass||!this._config)return h;let t=this.hass.states[this._config.entity];if(!t)return c`<hui-warning>${qt(this.hass,this._config.entity)}</hui-warning>`;let e=ot(t),s=t.attributes.hvac_action,o=Qs(t)?null:We[s],r=Ct(t),n=t.state==="unavailable",l=n?"var(--state-unavailable-color)":hs(r);return c`
      <ha-card style="--tile-color: ${l}">
        <div
          class="background"
          role="button"
          tabindex="0"
          @click=${()=>this._dialogOpen=!0}
          @keydown=${a=>{(a.key==="Enter"||a.key===" ")&&(this._dialogOpen=!0)}}
        ></div>
        <div class="container">
          <div class="content">
            <div class="icon">
              <ha-state-icon .hass=${this.hass} .stateObj=${t}></ha-state-icon>
              ${o?c`<div class="badge" style="--badge-color: ${Ge(s)}">
                    <ha-icon .icon=${o}></ha-icon>
                  </div>`:h}
            </div>
            <div class="info">
              <span class="primary">${Z(this.hass,t,this._config.name)}</span>
              <span class="secondary">${this._secondary(t)}</span>
            </div>
            <domo-status-icons
              ?window-open=${e.windowOpen}
              ?absent=${e.absent}
            ></domo-status-icons>
          </div>
          <div class="features">
            <div class="modes">
              ${this._modes(t).map(a=>c`<button
                  class=${a===r?"sel":""}
                  style="--btn-color: ${hs(a)}"
                  ?disabled=${n}
                  aria-label=${a}
                  @click=${()=>this._pick(a)}
                >
                  <ha-icon .icon=${Ht[a]||"mdi:thermostat"}></ha-icon>
                </button>`)}
            </div>
          </div>
        </div>
        ${this._dialogOpen?c`<domo-thermostat-dialog
              .hass=${this.hass}
              entity-id=${this._config.entity}
              step-minutes=${this._config.step_minutes}
              @closed=${()=>this._dialogOpen=!1}
            ></domo-thermostat-dialog>`:h}
      </ha-card>
    `}};m(pt,"properties",{hass:{attribute:!1},_config:{state:!0},_dialogOpen:{state:!0}}),m(pt,"styles",_`
    :host {
      display: block;
    }
    ha-card {
      position: relative;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      height: 100%;
      overflow: hidden;
    }
    .background {
      position: absolute;
      inset: 0;
      cursor: pointer;
      transition: background-color 180ms ease-in-out;
    }
    .background:active {
      background: rgba(var(--rgb-primary-text-color, 127, 127, 127), 0.06);
    }
    .container {
      position: relative;
      display: flex;
      flex-direction: column;
      flex: 1;
      pointer-events: none;
    }
    .content {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px;
      min-width: 0;
      box-sizing: border-box;
    }
    .icon {
      position: relative;
      flex: none;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 36px;
      height: 36px;
    }
    .icon ha-state-icon {
      position: relative;
      --mdc-icon-size: 24px;
      color: var(--tile-color);
      --icon-primary-color: var(--tile-color);
      transition: color 180ms ease-in-out;
    }
    .badge {
      position: absolute;
      top: -3px;
      right: -3px;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background-color: var(--badge-color);
      color: var(--white-color, #fff);
      transition: background-color 180ms ease-in-out;
    }
    .badge ha-icon {
      --mdc-icon-size: 12px;
      display: flex;
    }
    .info {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      justify-content: center;
      line-height: var(--ha-line-height-condensed, 1.2);
    }
    .primary,
    .secondary {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-size: var(--ha-font-size-m, 14px);
    }
    .primary {
      font-weight: var(--ha-font-weight-medium, 500);
      color: var(--primary-text-color);
    }
    .secondary {
      color: var(--secondary-text-color);
    }
    domo-status-icons {
      flex: none;
    }
    .features {
      padding: 0 12px 12px 12px;
      pointer-events: auto;
    }
    .modes {
      position: relative;
      display: flex;
      height: var(--feature-height, 42px);
      border-radius: var(--feature-border-radius, 12px);
      overflow: hidden;
    }
    .modes::before {
      content: "";
      position: absolute;
      inset: 0;
      background: var(--disabled-color);
      opacity: 0.2;
    }
    .modes button {
      position: relative;
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 0;
      padding: 0;
      background: none;
      color: var(--secondary-text-color);
      cursor: pointer;
      border-radius: var(--feature-border-radius, 12px);
      -webkit-tap-highlight-color: transparent;
    }
    .modes button[disabled] {
      cursor: default;
      opacity: 0.5;
    }
    .modes button.sel {
      background: var(--btn-color);
      color: var(--white-color, #fff);
    }
    .modes ha-icon {
      --mdc-icon-size: 24px;
      display: flex;
    }
  `);var ut=class extends g{_fire(t,e){this.dispatchEvent(new CustomEvent(t,{detail:e}))}render(){return c`<div class="panel">
      <div class="title">${f(this.hass,"dayTitle")}</div>
      <div class="chips">
        ${Y.map(t=>c`<button class="chip ${t===this.day?"on":""}" @click=${()=>this._fire("select",t)}>
            ${f(this.hass,t)}
          </button>`)}
      </div>
      <div class="btns">
        <button @click=${()=>this._fire("cancel")}>${f(this.hass,"cancel")}</button>
      </div>
    </div>`}};m(ut,"properties",{hass:{attribute:!1},day:{type:String}}),m(ut,"styles",_`
    :host {
      position: absolute;
      inset: 0;
      z-index: 30;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(0, 0, 0, 0.55);
      border-radius: var(--ha-card-border-radius, 12px);
    }
    .panel {
      width: 86%;
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color);
      border-radius: 16px;
      padding: 20px;
      box-sizing: border-box;
    }
    .title {
      font-size: 1.15rem;
      font-weight: 600;
      text-align: center;
      margin-bottom: 16px;
    }
    .chips {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
    }
    button {
      font: inherit;
      color: inherit;
      background: none;
      border: 0;
      cursor: pointer;
    }
    .chip {
      min-width: 0;
      padding: 9px 4px;
      border-radius: 24px;
      border: 2px solid transparent;
      background: var(--secondary-background-color, rgba(127, 127, 127, 0.2));
      font-weight: 700;
      text-align: center;
    }
    .chip.on {
      color: var(--primary-color);
      background-image: linear-gradient(rgba(var(--rgb-primary-color, 3, 169, 244), 0.14), rgba(var(--rgb-primary-color, 3, 169, 244), 0.14));
    }
    .btns {
      display: flex;
      margin-top: 20px;
    }
    .btns button {
      flex: 1;
      padding: 11px;
      border-radius: 24px;
      font-weight: 700;
      color: var(--primary-color);
      background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.14);
    }
  `);var ds="important",ti=" !"+ds,ee=at(class extends nt{constructor(i){if(super(i),i.type!==Zt.ATTRIBUTE||i.name!=="style"||i.strings?.length>2)throw Error("The `styleMap` directive must be used in the `style` attribute and must be the only part in the attribute.")}render(i){return Object.keys(i).reduce((t,e)=>{let s=i[e];return s==null?t:t+`${e=e.includes("-")?e:e.replace(/(?:^(webkit|moz|ms|o)|)(?=[A-Z])/g,"-$&").toLowerCase()}:${s};`},"")}update(i,[t]){let{style:e}=i.element;if(this.ft===void 0)return this.ft=new Set(Object.keys(t)),this.render(t);for(let s of this.ft)t[s]==null&&(this.ft.delete(s),s.includes("-")?e.removeProperty(s):e[s]=null);for(let s in t){let o=t[s];if(o!=null){this.ft.add(s);let r=typeof o=="string"&&o.endsWith(ti);s.includes("-")||r?e.setProperty(s,r?o.slice(0,-11):o,r?ds:""):e[s]=o}}return E}});var ps=_`
  :host {
    position: relative;
    display: block;
    height: 100%;
  }
  ha-card {
    position: relative;
    height: 100%;
    width: 100%;
    padding: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: space-between;
  }

  .title {
    width: 100%;
    font-size: var(--ha-font-size-l, 16px);
    line-height: var(--ha-line-height-expanded, 1.5);
    padding: 8px 30px 8px 30px;
    margin: 0;
    text-align: center;
    box-sizing: border-box;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: none;
  }

  .container {
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
    max-width: 100%;
    box-sizing: border-box;
    flex: 1;
  }

  .container:before {
    content: "";
    display: block;
    padding-top: 100%;
  }

  .container > * {
    padding: 8px;
  }

  .container > .status {
    position: absolute;
    padding: 0;
  }

  .more-info {
    position: absolute;
    cursor: pointer;
    top: 0;
    right: 0;
    inset-inline-end: 0px;
    inset-inline-start: initial;
    border-radius: var(--ha-border-radius-pill, 9999px);
    color: var(--secondary-text-color);
    direction: var(--direction);
  }

  hui-card-features {
    width: 100%;
    flex: none;
    padding: 0 12px 12px 12px;
  }
`;var mt=class extends g{static getConfigElement(){return document.createElement(Rt)}static getStubConfig(t,e,s){let r=[...e||[],...s||[]].find(l=>l.startsWith("climate.")),n=Object.keys(t?.states||{}).find(l=>l.startsWith("climate."));return{type:`custom:${ft}`,entity:r||n||""}}constructor(){super(),this._featureContext={},this._ready=!1,this._dialogOpen=!1,this._resizeObserver=new ResizeObserver(()=>this._measure())}getCardSize(){return 7}setConfig(t){if(!t||!t.entity||!zt.includes(t.entity.split(".")[0]))throw new Error("Specify an entity from within the climate or water_heater domain");let e=Number(t.step_minutes);this._config={...t,step_minutes:Nt.includes(e)?e:It},this._featureContext={entity_id:t.entity}}getGridOptions(){let e=5,s=2,o=6;if(this._config?.features?.length){let r=Math.ceil(this._config.features.length*2/3);e+=r,s+=r}return{columns:12,rows:e,min_columns:o,min_rows:s}}connectedCallback(){super.connectedCallback(),this._resizeObserver.observe(this),this._config&&At(this._config.entity).then(()=>{this._ready=!0})}disconnectedCallback(){super.disconnectedCallback(),this._resizeObserver.disconnect(),this._dialogOpen=!1}_measure(){let e=this.shadowRoot?.querySelector(".container")?.clientHeight;this._controlMaxWidth=e?`${e}px`:void 0,this._placeOverlays()}_placeOverlays(){let t=this.shadowRoot?.querySelector(".container"),e=t?.querySelector("ha-state-control-climate-temperature");if(!e)return;let s=this.hass?.states[this._config.entity],o=()=>Ft(e,!!s&&X(s));o(),e.updateComplete?.then(o),Yt(t,e,t.querySelector(".status"))}_handleMoreInfo(){Bt(this._config.entity)==="climate"?this._dialogOpen=!0:L(this,"hass-more-info",{entityId:this._config.entity})}updated(t){if(super.updated(t),!this._config||!this.hass||((t.has("_ready")||t.has("_config"))&&this._measure(),t.has("hass")&&this._placeOverlays(),!t.has("hass")&&!t.has("_config")))return;let e=t.get("hass"),s=t.get("_config");(!e||!s||e.themes!==this.hass.themes||s.theme!==this._config.theme)&&Jt(this,this.hass.themes,this._config.theme)}render(){if(!this.hass||!this._config)return h;let t=this.hass.states[this._config.entity];if(!t)return c`<hui-warning>
        ${qt(this.hass,this._config.entity)}
      </hui-warning>`;this._ready||At(this._config.entity).then(()=>{this._ready=!0});let e=Bt(t.entity_id),s=Z(this.hass,t,this._config.name),o=Ye(t),r=this._controlMaxWidth,n=e==="climate"?ot(t):{};return c`
      <ha-card>
        <p class="title">${s}</p>
        <div class="container">
          ${e==="water_heater"?c`<ha-state-control-water_heater-temperature
                style=${ee({maxWidth:r})}
                prevent-interaction-on-scroll
                show-current
                .stateObj=${t}
              ></ha-state-control-water_heater-temperature>`:c`<ha-state-control-climate-temperature
                style=${ee({maxWidth:r})}
                prevent-interaction-on-scroll
                .hass=${this.hass}
                .showCurrentAsPrimary=${this._config.show_current_as_primary}
                show-secondary
                .stateObj=${t}
              ></ha-state-control-climate-temperature>`}
          ${e==="climate"?c`<domo-status-icons
                class="floating status"
                ?window-open=${n.windowOpen}
                ?absent=${n.absent}
              ></domo-status-icons>`:h}
        </div>
        <ha-icon-button
          class="more-info"
          .label=${this.hass.localize("ui.panel.lovelace.cards.show_more_info")}
          .path=${xe}
          @click=${this._handleMoreInfo}
          tabindex="0"
        ></ha-icon-button>
        ${this._config.features?.length?c`<hui-card-features
              style=${ee({"--feature-color":o})}
              .hass=${this.hass}
              .context=${this._featureContext}
              .features=${this._config.features}
            ></hui-card-features>`:h}
        ${this._dialogOpen?c`<domo-thermostat-dialog
              .hass=${this.hass}
              entity-id=${this._config.entity}
              step-minutes=${this._config.step_minutes}
              @closed=${()=>{this._dialogOpen=!1}}
            ></domo-thermostat-dialog>`:h}
      </ha-card>
    `}};m(mt,"properties",{hass:{attribute:!1},_config:{state:!0},_featureContext:{state:!0},_controlMaxWidth:{state:!0},_ready:{state:!0},_dialogOpen:{state:!0}}),m(mt,"styles",ps);var ei=[["domo-status-icons",it],["domo-feature-button",et],["domo-feature-select",st],["domo-program-dial",lt],["domo-hour-zoom",ct],["domo-temp-fields",ht],["domo-copy-dialog",rt],["domo-day-dialog",ut],["domo-thermostat-dialog",dt],[Rt,J],[jt,te],[ft,mt],[gt,pt]],si=[[ft,"Domo Thermostat","Replica della Thermostat Card nativa per i termostati dell'integrazione domo."],[gt,"Domo Thermostat Minimal","Replica della tile card nativa con modalit\xE0, Jolly e icone finestra/presenza."]],ii=1e4;async function oi(){await Promise.race([window.customElements.whenDefined("home-assistant"),new Promise(i=>setTimeout(i,ii))]);for(let[i,t]of ei)window.customElements.get(i)||window.customElements.define(i,t);window.customCards=window.customCards||[];for(let[i,t,e]of si)window.customCards.some(s=>s.type===i)||window.customCards.push({type:i,name:t,description:e,preview:!0})}oi();
/*! Bundled license information:

@lit/reactive-element/css-tag.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/reactive-element.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/lit-html.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-element/lit-element.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/is-server.js:
  (**
   * @license
   * Copyright 2022 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/directive.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/directives/unsafe-html.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/directives/unsafe-svg.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/directives/style-map.js:
  (**
   * @license
   * Copyright 2018 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*/
