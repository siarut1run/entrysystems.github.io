import {getEnv,owner,error,need} from '../../../lib/entry';
export const dynamic='force-dynamic';
export async function GET(req:Request){
 try{
  owner(req);
  const e=getEnv();
  need(e.BRIDGE_KEY&&e.BRIDGE_DISPATCH_TOKEN,'接続設定が準備されていません。運営にお問い合わせください。');
  const config=`DISCORD_TOKEN=\nSITE_URL=${e.SITE_ORIGIN||new URL(req.url).origin}\nENTRY_KEY=${e.BRIDGE_KEY}\nSITE_SERVICE_TOKEN=${e.BRIDGE_DISPATCH_TOKEN}\n`;
  if(new URL(req.url).searchParams.get('format')==='json')return Response.json({filename:'connection.env',config},{headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
  return new Response(config,{headers:{'Content-Type':'text/plain; charset=utf-8','Content-Disposition':'attachment; filename="connection.env"','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
 }catch(e){return error(e)}
}
