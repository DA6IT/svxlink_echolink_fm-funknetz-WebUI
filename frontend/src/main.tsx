import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import './style.css';

type Event = {event:string; callsign:string; timestamp:string};
type Status = {node:Record<string, string|number>; svxlink:{status:string;pid:number|null;substate:string}; reflector:{events:Event[];count:number;last_heard:Event|null;available:boolean}; config:Record<string,Record<string,string>>; demo:boolean; updated_at:string};
const api='/api';
const value=(obj:Record<string, unknown>, ...keys:string[]) => keys.map(k=>obj[k]).find(v=>v !== undefined && v !== null && v !== '') as string|number|undefined;
function Card({title,value:content,detail,active=false}:{title:string;value:string;detail?:string;active?:boolean}) { return <article className={'card '+(active?'active':'')}><small>{title}</small><strong>{content}</strong>{detail&&<span>{detail}</span>}</article>; }
function App() {
  const [s,setS]=useState<Status|null>(null); const [err,setErr]=useState('');
  useEffect(()=>{const load=()=>fetch(api+'/status').then(r=>{if(!r.ok) throw Error(); return r.json();}).then(setS).catch(()=>setErr('Backend nicht erreichbar.')); load(); const timer=setInterval(load,15000); return()=>clearInterval(timer);},[]);
  if(err)return <main><h1>{err}</h1></main>; if(!s)return <main><p>Lade Live-Status …</p></main>;
  const n=s.node; const name=String(value(n,'Callsign','CALLSIGN','nodeLocation','Location')||'SvxLink Node'); const freq=value(n,'TXFREQ','RXFREQ')||'nicht verfügbar'; const logics=Object.values(s.config).map(c=>c.LOGICS).filter(Boolean).join(', ')||'nicht konfiguriert'; const last=s.reflector.last_heard;
  return <><header><div><small>SVXLINK · FM-FUNKNETZ</small><h1>{name}</h1><p>{value(n,'Location','nodeLocation')||'Standort nicht konfiguriert'} · {freq} MHz</p></div><b className="badge">{s.demo?'DEMO':'LIVE'}</b></header><main>
    <section className="hero"><div><small>SVXLINK-SERVICE</small><h2>{s.svxlink.status==='online'?'Online':'Nicht verfügbar'}</h2><p>{s.svxlink.status==='online'?`Dienst läuft · PID ${s.svxlink.pid||'—'} · ${s.svxlink.substate}`:'Dienststatus konnte nicht ermittelt werden'}</p></div></section>
    <section className="grid"><Card title="Station / Standort" value={name} detail={String(value(n,'Locator','LAT')||'Koordinaten nicht verfügbar')}/><Card title="Frequenz" value={`${freq} MHz`} detail={`RX ${value(n,'RXFREQ')||'—'} · Mode ${value(n,'Mode')||'—'}`}/><Card title="Default-TG" value={String(value(Object.assign({},...Object.values(s.config)),'DEFAULT_TG')||'nicht konfiguriert')} detail="Allowlisted INI-Wert"/><Card title="Reflector-Aktivität" value={`${s.reflector.count} Ereignisse`} detail={s.reflector.available?'Aus lokalen SvxLink-Logs':'Logquelle nicht verfügbar'} active={s.reflector.count>0}/><Card title="Last Heard" value={last?`${last.callsign} · ${last.event}`:'Keine Ereignisse'} detail={last?.timestamp||'—'}/><Card title="Logics / NetLink" value={logics} detail="Allowlisted Konfiguration"/></section>
    <section className="events"><div className="section-heading"><h3>Letzte Reflector-Ereignisse</h3><small>Aktualisiert {new Date(s.updated_at).toLocaleTimeString('de-DE')}</small></div>{s.reflector.events.slice(-8).reverse().map((e,i)=><div className="event" key={`${e.timestamp}-${i}`}><b>{e.callsign}</b><span>{e.event==='joined'?'beigetreten':'verlassen'}</span><time>{e.timestamp}</time></div>)}{!s.reflector.events.length&&<p>Keine lokalen Join/Leave-Ereignisse im verfügbaren Log.</p>}</section>
  </main><nav>Read-only · Keine Steuerbefehle · Keine Secrets</nav></>;
}
createRoot(document.getElementById('root')!).render(<App/>);
