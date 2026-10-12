export async function apiJSON(path:string,init:RequestInit={}){
 const headers=new Headers(init.headers);headers.set('Accept','application/json');
 let response:Response;
 try{response=await fetch(path,{...init,headers,credentials:'same-origin',cache:'no-store',signal:init.signal??AbortSignal.timeout(20000)});}catch{throw new Error('通信できませんでした。サイトを開き直して再試行してください。');}
 const body=await response.text();
 if(/^\s*</.test(body)){
  if(response.redirected||[401,403].includes(response.status))throw new Error('ログイン状態を確認してください。サイトを新しいタブで開き直して再試行してください。');
  throw new Error(`サイトからデータを取得できませんでした（HTTP ${response.status}）。ページを再読み込みして再試行してください。`);
 }
 let value:any;
 try{value=JSON.parse(body);}catch{throw new Error(`サーバーの応答を読み込めませんでした（HTTP ${response.status}）。再試行してください。`);}
 if(!response.ok)throw new Error(typeof value?.error==='string'?value.error:`処理に失敗しました（HTTP ${response.status}）。`);
 return value;
}
