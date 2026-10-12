import type {State,Team,Member} from './entry';
import {ensure,mutable} from './workflows';
export function editable(s:State,m:Member){ensure(!m.removing&&m.status!=='removed','このメンバーは解除済み、または解除処理中です。');const t=s.teams.find(t=>t.id===m.team);ensure(t&&!['deleting','deleted'].includes(t.status),'チームを削除中、または削除済みです。');}
export function cancelRelated(s:State,memberIds:string[],teamId?:string){
 const changes=s.changes.filter(c=>memberIds.includes(c.member)||teamId&&c.target===teamId);
 const refs=new Set([...memberIds,...changes.map(c=>c.id),...(teamId?[teamId]:[])]);
 ensure(!s.jobs.some(j=>refs.has(j.ref)&&j.status==='running'),'Discord処理中です。完了してから再操作してください。');
 for(const j of s.jobs)if(refs.has(j.ref)&&['pending','failed'].includes(j.status)){j.status='cancelled';j.error=undefined;}
 for(const c of changes)if(['pending','returned','applying'].includes(c.status)){c.status='cancelled';c.error=undefined;}
}
export function prepareMemberRemoval(s:State,m:Member){mutable(s.events.find(e=>e.id===m.event)!);editable(s,m);ensure(['pending','returned','approving','approved'].includes(m.status),'このメンバーは登録解除の対象ではありません。');cancelRelated(s,[m.id]);m.removing=true;m.error=undefined;}
export function prepareTeamDeletion(s:State,t:Team){mutable(s.events.find(e=>e.id===t.event)!);ensure(!['deleting','deleted'].includes(t.status),'チームを削除中、または削除済みです。');const members=s.members.filter(m=>m.team===t.id);cancelRelated(s,members.map(m=>m.id),t.id);t.enabled=false;t.status='deleting';t.error=undefined;for(const m of members){m.removing=true;m.error=undefined;}}
