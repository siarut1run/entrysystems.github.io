import { env } from 'cloudflare:workers';
export type Position='player'|'coach'|'reserve';
export type Registration={open:boolean;deadline:string;finalized:boolean;minMembers:number;maxPoints:number|null;panel:string;changePanel:string;title:string;description:string};
export type ChangeRequest={id:string;member:string;event:string;kind:'correction'|'transfer'|'withdraw';target?:string;info?:{xid:string;tracker:string;rank:string;riotId?:string;displayName?:string;position?:Position};reason:string;status:string;created:string;reviewReason?:string;error?:string};
export type Event={id:string;name:string;guild:string;points:Record<string,number>;registration?:Registration};
export type Team={id:string;event:string;name:string;code:string;capacity:number;number?:number;enabled:boolean;role?:string;category?:string;chat?:string;vc?:string;status:string;error?:string};
export type Member={id:string;team:string;event:string;user:string;name:string;xid:string;tracker:string;rank:string;riotId?:string;displayName?:string;position?:Position;status:string;created:string;error?:string;reason?:string;removing?:boolean};
export type Job={id:string;kind:string;ref:string;status:string;error?:string;lease?:number};
export type State={events:Event[];teams:Team[];members:Member[];jobs:Job[];settings:Record<string,{unverified:string;verified:string;review:string;panel:string}>;guilds:{id:string;name:string}[];heartbeat:number;changes:ChangeRequest[]};
export const ranks=['UNRANKED',...['IRON','BRONZE','SILVER','GOLD','PLATINUM','DIAMOND','ASCENDANT','IMMORTAL'].flatMap(r=>[1,2,3].map(n=>`${r} ${n}`)),'RADIANT'];
export const fresh=():State=>({events:[],teams:[],members:[],jobs:[],settings:{},guilds:[],heartbeat:0,changes:[]});
const runtime=env as unknown as {DB:D1Database;BRIDGE_KEY:string;BRIDGE_DISPATCH_TOKEN:string;SITE_ORIGIN:string};
export const getEnv=()=>runtime;
export function normalize(s:State){s.changes??=[];for(const e of s.events){const teams=s.teams.filter(t=>t.event===e.id);const used=new Set(teams.map(t=>t.number).filter((n):n is number=>Number.isInteger(n)&&Number(n)>0));let next=1;for(const t of teams)if(!Number.isInteger(t.number)||Number(t.number)<1){while(used.has(next))next++;t.number=next;used.add(next);}}return s;}
export async function read(){const row=await runtime.DB.prepare("SELECT data,version FROM entry_state WHERE id=?").bind('main').first<{data:string;version:number}>();return row?{state:normalize(JSON.parse(row.data)),version:row.version}:{state:fresh(),version:-1};}
export async function change<T>(fn:(s:State)=>T){
 for(let n=0;n<8;n++){
  const {state,version}=await read();const result=fn(state);
  const json=JSON.stringify(state); if(json.length>4000000)throw new Error('登録件数の上限です。');
  const r=version<0?await runtime.DB.prepare('INSERT OR IGNORE INTO entry_state(id,data,version) VALUES(?,?,0)').bind('main',json).run():await runtime.DB.prepare('UPDATE entry_state SET data=?,version=version+1 WHERE id=? AND version=?').bind(json,'main',version).run();
  if(r.meta.changes)return result;
 }throw new Error('別の更新と重なりました。再試行してください。');
}
export function need(v:unknown,msg:string):asserts v{if(!v)throw new Error(msg)}
export function text(v:unknown,max=80){need(typeof v==='string'&&v.trim().length>0&&v.trim().length<=max,'入力内容を確認してください。');return v.trim()}
export function snow(v:unknown){const t=text(v,25);need(/^\d{17,20}$/.test(t),'Discord IDは17〜20桁の数字です。');return t}
export const id=()=>crypto.randomUUID();
export function code(){const a=new Uint8Array(8);crypto.getRandomValues(a);return [...a].map(n=>n.toString(16).padStart(2,'0')).join('').toUpperCase()}
export function job(s:State,kind:string,ref:string){s.jobs.push({id:id(),kind,ref,status:'pending'});}
export function total(s:State,t:Team){const e=s.events.find(e=>e.id===t.event)!;const ms=s.members.filter(m=>m.team===t.id&&m.status==='approved');return {count:ms.length,points:ms.reduce((n,m)=>n+(e.points[m.rank]??0),0),missing:ms.filter(m=>e.points[m.rank]===undefined).length};}
export async function isBridge(req:Request){const k=req.headers.get('x-entry-key')??'';if(!runtime.BRIDGE_KEY||k.length!==runtime.BRIDGE_KEY.length)return false;const a=new TextEncoder().encode(k);const b=new TextEncoder().encode(runtime.BRIDGE_KEY);let d=0;for(let n=0;n<a.length;n++)d|=a[n]^b[n];return d===0;}
export function owner(req:Request){need(req.headers.get('oai-authenticated-user-id'),'ログインしてください。');}
export function sameOrigin(req:Request){need(req.headers.get('origin')===(runtime.SITE_ORIGIN||new URL(req.url).origin),'無効なリクエストです。');}
export function error(e:unknown){console.error(e);return Response.json({error:e instanceof Error?e.message:'処理に失敗しました。'},{status:400});}
