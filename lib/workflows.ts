export const positionLabels:Record<string,string>={player:'選手',coach:'コーチ',reserve:'リザーブ'};
import type {State,Event,Team,Registration,Position} from './entry';
export const rankNames=['UNRANKED',...['IRON','BRONZE','SILVER','GOLD','PLATINUM','DIAMOND','ASCENDANT','IMMORTAL'].flatMap(r=>[1,2,3].map(n=>`${r} ${n}`)),'RADIANT'];
export function ensure(v:unknown,message:string):asserts v {if(!v)throw Error(message)}
export function registration(e:Event):Registration{return {open:true,deadline:'',finalized:false,minMembers:5,maxPoints:null,panel:'',changePanel:'',title:'大会メンバー登録',description:'チームコードを入力し、個人情報を登録してください。',...e.registration}}
export function intake(e:Event){const r=registration(e);ensure(!r.finalized,'登録が確定済みです。運営にお問い合わせください。');ensure(r.open,'登録受付を停止しています。');ensure(!r.deadline||Date.now()<Date.parse(r.deadline),'登録締切を過ぎています。');}
export function mutable(e:Event){ensure(!registration(e).finalized,'登録が確定済みです。運営にお問い合わせください。');}
export function occupancy(s:State,t:Team){return s.members.filter(m=>m.team===t.id&&['pending','returned','approving','approved'].includes(m.status)).length+s.changes.filter(c=>c.target===t.id&&['pending','applying'].includes(c.status)).length;}
export function riotFromTracker(tracker:string){try{const u=new URL(tracker);if(u.protocol!=='https:'||u.hostname!=='tracker.gg')return '';const match=u.pathname.match(/^\/valorant\/profile\/riot\/([^/]+)\//);return match?decodeURIComponent(match[1]):'';}catch{return '';}}
export function riotLabel(m:{riotId?:string;tracker?:string}){return m.riotId||riotFromTracker(m.tracker??'');}
export function trackerURL(riotId:string){return `https://tracker.gg/valorant/profile/riot/${encodeURIComponent(riotId)}/overview`;}
export function profile(b:Record<string,any>,fallback:Position='player',fallbackDisplay?:string){
 let xid=String(b.xid??'').trim().replace(/^@/,'').replace(/^https:\/\/(x.com|twitter.com)\//,'').replace(/\/$/,'');ensure(/^[A-Za-z0-9_]{1,15}$/.test(xid),'X IDを確認してください。');
 let tracker:string,riotId:string;
 if(b.riotId!==undefined){
  ensure(typeof b.riotId==='string','Riot IDを入力してください。');riotId=b.riotId.trim();
  ensure(riotId.length<=100&&/^[^#\/\r\n\u0000-\u001f]+#[^#\/\r\n\u0000-\u001f]+$/.test(riotId),'Riot IDは「名前#タグ」の形式で入力してください。');
  ensure(riotId.split('#').every(part=>part.trim().length>0),'Riot IDの名前とタグを入力してください。');tracker=trackerURL(riotId);
 }else{
  tracker=String(b.tracker??'').trim();let u:URL;try{u=new URL(tracker)}catch{throw Error('Riot IDを入力してください。')}
  ensure(tracker.length<=500&&u.protocol==='https:'&&u.hostname==='tracker.gg'&&!u.username&&!u.password&&/^\/valorant\/profile\/riot\/[^/]+\//.test(u.pathname),'Riot IDを入力してください。');riotId=riotFromTracker(tracker);
 }
 const displayName=b.displayName??fallbackDisplay;
 if(displayName!==undefined)ensure(typeof displayName==='string'&&displayName.trim().length>0&&displayName.trim().length<=100&&!/[\u0000-\u001f]/.test(displayName),'表示名（配信記載）を1〜100文字で入力してください。');
 const rank=String(b.rank??'').trim().toUpperCase().replace(/\s+/g,' ');ensure(rankNames.includes(rank),'最高ランクの形式を確認してください。');
 const position=b.position??fallback;ensure(['player','coach','reserve'].includes(position),'参加区分を選択してください。');
 return {xid,tracker,riotId,rank,position:position as Position,...(displayName!==undefined?{displayName:displayName.trim()}:{})};
}
export function issues(s:State,t:Team){const e=s.events.find(e=>e.id===t.event)!;const r=registration(e),ms=s.members.filter(m=>m.team===t.id),approved=ms.filter(m=>m.status==='approved'),out:string[]=[];if(t.status==='deleting')out.push('チーム削除処理中');if(ms.some(m=>m.removing))out.push('メンバー解除処理中');if(t.status!=='ready')out.push('Discordチーム作成未完了');if(!ms.some(m=>!['rejected','withdrawn','removed'].includes(m.status)))out.push('未登録');if(approved.length<r.minMembers)out.push(`人数不足 ${approved.length}/${r.minMembers}人`);if(approved.length>t.capacity)out.push('定員超過');const n=ms.filter(m=>m.status==='pending').length;if(n)out.push(`承認待ち ${n}人`);const returned=ms.filter(m=>m.status==='returned').length;if(returned)out.push(`修正待ち ${returned}人`);if(ms.some(m=>m.status==='approving'))out.push('ロール付与待ち');if(approved.some(m=>e.points[m.rank]===undefined))out.push('ランクポイント未設定');if(r.maxPoints!==null&&approved.reduce((n,m)=>n+(e.points[m.rank]??0),0)>r.maxPoints)out.push('上限ポイント超過');if(s.changes.some(c=>c.event===e.id&&['pending','applying','returned'].includes(c.status)&&ms.some(m=>m.id===c.member)))out.push('変更・辞退の未処理申請');return out;}
