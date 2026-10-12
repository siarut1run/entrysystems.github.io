import os, asyncio, logging, time
from urllib.parse import unquote, urlparse
import aiohttp, discord
from discord.ext import tasks
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'connection.env' if os.path.isfile(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'connection.env')) else '.env'));logging.basicConfig(level=logging.INFO)
SITE=os.getenv('SITE_URL','').rstrip('/'); KEY=os.getenv('ENTRY_KEY',''); SERVICE=os.getenv('SITE_SERVICE_TOKEN','')
state={}; attempts={}
async def api(action=None,**payload):
    headers={'x-entry-key':KEY,'OAI-Sites-Authorization':'Bearer '+SERVICE}
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        if action:
            async with session.post(SITE+'/api/bridge',headers=headers,json={'action':action,**payload},allow_redirects=False) as r:
                try:d=await r.json()
                except Exception:raise ValueError('サイトとの接続に失敗しました。接続設定を確認してください。')
                if r.status!=200:raise ValueError(d.get('error','サイトとの接続に失敗しました。'))
        else:
            async with session.get(SITE+'/api/bridge',headers=headers,allow_redirects=False) as r:
                try:d=await r.json()
                except Exception:raise ValueError('サイトとの接続に失敗しました。接続設定を確認してください。')
                if r.status!=200:raise ValueError(d.get('error','サイトとの接続に失敗しました。'))
                return d
        if d.get('error'):raise ValueError(d['error'])
        return d.get('result')
async def reply_error(i,e):
    logging.exception('Interaction error')
    msg=str(e) if isinstance(e,ValueError) else '処理に失敗しました。運営にお問い合わせください。'
    if i.response.is_done():await i.followup.send(msg,ephemeral=True)
    else:await i.response.send_message(msg,ephemeral=True)
RANK_OPTIONS=[(f'{tier} {n}',f'{tier} {n}') for tier in ['IRON','BRONZE','SILVER','GOLD','PLATINUM','DIAMOND','ASCENDANT','IMMORTAL'] for n in [1,2,3]]+[('RADIANT','RADIANT')]
POSITION_OPTIONS=[('選手','player'),('コーチ','coach'),('リザーブ','reserve')]
def riot_id(info):
    if not info:return ''
    if info.get('riotId'):return info['riotId']
    try:
        url=urlparse(info.get('tracker',''));parts=url.path.split('/')
        if url.hostname=='tracker.gg' and parts[1:4]==['valorant','profile','riot']:return unquote(parts[4])
    except (ValueError,IndexError):pass
    return ''
class Info(discord.ui.Modal,title='個人情報を登録'):
    def __init__(self,team,user,event=None,mode='submit',info=None):
        super().__init__();self.team=team;self.user=user;self.event=event;self.mode=mode
        self.xid=discord.ui.TextInput(placeholder='@MASTERPRIMECUP',max_length=100,default=info['xid'] if info else None)
        self.riotId=discord.ui.TextInput(placeholder='MasterPrimeCup#gg',max_length=100,default=riot_id(info) or None)
        self.displayName=discord.ui.TextInput(placeholder='配信に記載する名前',max_length=100,default=(info.get('displayName') or info.get('name')) if info else None)
        self.rank=discord.ui.Select(placeholder='最高ランクを選択',min_values=1,max_values=1,required=True,options=[discord.SelectOption(label=label,value=value,default=bool(info and info['rank']==value)) for label,value in RANK_OPTIONS])
        self.position=discord.ui.Select(placeholder='参加区分を選択',min_values=1,max_values=1,required=True,options=[discord.SelectOption(label=label,value=value,default=bool(info and info.get('position','player')==value)) for label,value in POSITION_OPTIONS])
        for label,component in [('X ID',self.xid),('Riot ID',self.riotId),('表示名（配信記載）',self.displayName),('最高ランク',self.rank),('参加区分',self.position)]:self.add_item(discord.ui.Label(text=label,component=component))
    async def on_submit(self,i):
        if i.user.id!=self.user:raise ValueError('本人のみ操作できます。')
        if len(self.rank.values)!=1 or self.rank.values[0] not in [value for _,value in RANK_OPTIONS]:raise ValueError('最高ランクを選択してください。')
        if len(self.position.values)!=1 or self.position.values[0] not in [value for _,value in POSITION_OPTIONS]:raise ValueError('参加区分を選択してください。')
        await i.response.defer(ephemeral=True)
        result=await api('requestChange' if self.mode=='correction' else 'submit',kind='correction',event=self.event,team=self.team,guild=str(i.guild_id),user=str(i.user.id),name=i.user.display_name,xid=str(self.xid),riotId=str(self.riotId),displayName=str(self.displayName),rank=self.rank.values[0],position=self.position.values[0])
        await i.followup.send('申請を保存しました。運営の承認をお待ちください。',ephemeral=True)
    async def on_error(self,i,e):await reply_error(i,e)
class Continue(discord.ui.View):
    def __init__(self,team,user):super().__init__(timeout=300);self.team=team;self.user=user
    @discord.ui.button(label='個人情報を入力',style=discord.ButtonStyle.primary)
    async def go(self,i,b):
        if i.user.id!=self.user:return await i.response.send_message('本人のみ操作できます。',ephemeral=True)
        await i.response.send_modal(Info(self.team,self.user))
class Code(discord.ui.Modal,title='チームコード入力'):
    def __init__(self,event=None):super().__init__();self.event=event
    code=discord.ui.TextInput(label='チーム専用コード',max_length=32)
    async def on_submit(self,i):
        now=time.monotonic(); key=(i.guild_id,i.user.id); recent=[n for n in attempts.get(key,[]) if now-n<60]
        if len(recent)>=5:raise ValueError('1分後に再試行してください。')
        attempts[key]=recent+[now]
        await i.response.defer(ephemeral=True)
        team=await api('code',guild=str(i.guild_id),event=self.event,code=str(self.code))
        await i.followup.send(f"大会：{team['event']}\nチーム：{team['name']}",view=Continue(team['id'],i.user.id),ephemeral=True,allowed_mentions=discord.AllowedMentions.none())
    async def on_error(self,i,e):await reply_error(i,e)
class ChangeModal(discord.ui.Modal):
    def __init__(self,event,kind):
        super().__init__(title='チーム変更申請' if kind=='transfer' else '辞退申請');self.event=event;self.kind=kind
        if kind=='transfer':
            self.code=discord.ui.TextInput(label='移動先チームコード',max_length=32);self.add_item(self.code)
        self.reason=discord.ui.TextInput(label='申請理由',style=discord.TextStyle.paragraph,max_length=1000);self.add_item(self.reason)
    async def on_submit(self,i):
        await i.response.defer(ephemeral=True)
        await api('requestChange',event=self.event,kind=self.kind,guild=str(i.guild_id),user=str(i.user.id),code=str(self.code) if self.kind=='transfer' else '',reason=str(self.reason))
        await i.followup.send('申請を保存しました。運営の承認まで現在の登録を維持します。',ephemeral=True)
    async def on_error(self,i,e):await reply_error(i,e)
class EditContinue(discord.ui.View):
    def __init__(self,event,m,user):super().__init__(timeout=300);self.event=event;self.m=m;self.user=user
    @discord.ui.button(label='登録情報を修正',style=discord.ButtonStyle.primary)
    async def edit(self,i,b):
        if i.user.id!=self.user:return await i.response.send_message('本人のみ操作できます。',ephemeral=True)
        info={**self.m,**((self.m.get('change') or {}).get('info') or {})}
        await i.response.send_modal(Info(self.m['team'],self.user,self.event,'correction' if self.m['status']=='approved' else 'submit',info))
class Panel(discord.ui.View):
    def __init__(self,event=None,changes=False):
        super().__init__(timeout=None);self.event=event
        options=[('チーム変更を申請','transfer'),('辞退を申請','withdraw')] if changes else [('チームコードを入力','register')]
        if event and not changes:options.append(('修正・再申請','edit'))
        for label,kind in options:
            button=discord.ui.Button(label=label,style=discord.ButtonStyle.primary if kind=='register' else discord.ButtonStyle.secondary,custom_id=f"radius-entry:{event+':' if event else ''}{kind}")
            async def callback(i,kind=kind):
                try:
                    if kind=='register':return await i.response.send_modal(Code(self.event))
                    if kind in ['transfer','withdraw']:return await i.response.send_modal(ChangeModal(self.event,kind))
                    await i.response.defer(ephemeral=True)
                    m=await api('member',event=self.event,guild=str(i.guild_id),user=str(i.user.id))
                    reason=(m.get('change') or {}).get('reviewReason') or m.get('reason')
                    await i.followup.send(('差し戻し理由：'+reason+'\n' if reason else '')+'登録情報を修正してください。承認済み情報の変更は運営の承認後に反映します。',view=EditContinue(self.event,m,i.user.id),ephemeral=True,allowed_mentions=discord.AllowedMentions.none())
                except Exception as e:await reply_error(i,e)
            button.callback=callback;self.add_item(button)
def team_label(t,s):
    number=t.get('number') or next(n for n,team in enumerate([team for team in s['teams'] if team['event']==t['event']],1) if team['id']==t['id'])
    return f"{number:02d}_{t['name']}"
class Bot(discord.Client):
    def __init__(self):
        intents=discord.Intents.default();intents.members=True
        super().__init__(intents=intents,allowed_mentions=discord.AllowedMentions.none())
    async def setup_hook(self):
        self.add_view(Panel());self.registered=set();self.worker.start()
    def register_panels(self,s):
        for e in s['events']:
            if e['id'] not in self.registered:
                self.add_view(Panel(e['id']));self.add_view(Panel(e['id'],True));self.registered.add(e['id'])
    async def on_member_join(self,m):
        try:
            s=await api();cfg=s['settings'].get(str(m.guild.id))
            if not cfg:return
            evs=[e['id'] for e in s['events'] if e['guild']==str(m.guild.id)]
            accepted=[r for r in s['members'] if r['event'] in evs and r['user']==str(m.id) and r['status']=='approved' and not r.get('removing') and any(t['id']==r['team'] and t['status']=='ready' for t in s['teams'])]
            ids=[cfg['unverified']]
            if accepted:
                ids=[cfg['verified']]+[t['role'] for t in s['teams'] if any(r['team']==t['id'] for r in accepted) and t.get('role')]
            roles=[m.guild.get_role(int(n)) for n in ids]
            if any(r is None for r in roles):raise ValueError('設定ロールが見つかりません。')
            await m.add_roles(*roles,reason='大会入室：認証ロール')
        except Exception:logging.exception('Join role failed')
    @tasks.loop(seconds=5,reconnect=True)
    async def worker(self):
        global state
        try:
            await api('heartbeat',guilds=[{'id':str(g.id),'name':g.name} for g in self.guilds])
            j=await api('lease')
            state=await api();self.register_panels(state)
            if not j:return
            try:
                await self.execute(j,state)
                await api('done',id=j['id'])
            except Exception as e:
                logging.exception('Discord task failed')
                await api('done',id=j['id'],error=str(e)[:900] or 'Discord処理に失敗しました。')
        except Exception:logging.exception('Site bridge unavailable')
    @worker.before_loop
    async def before_worker(self):await self.wait_until_ready()
    def config(self,s,guild):
        g=self.get_guild(int(guild))
        if not g:raise ValueError('Botがサーバーに参加していません。')
        cfg=s['settings'].get(guild)
        if not cfg:raise ValueError('サイトでDiscord設定を保存してください。')
        for n in ['unverified','verified']:
            role=g.get_role(int(cfg[n]))
            if not role or role.is_default() or role.managed or role>=g.me.top_role:raise ValueError('未認証・認証済みロールをBotより下に置いてください。')
        review=g.get_channel(int(cfg['review']))
        if not review or not isinstance(review,discord.TextChannel):raise ValueError('運営承認チャンネルが見つかりません。')
        for role in [g.default_role,g.get_role(int(cfg['unverified'])),g.get_role(int(cfg['verified']))]:
            if review.permissions_for(role).view_channel:raise ValueError('運営承認チャンネルは一般・未認証・認証済みから非公開にしてください。')
        return g,cfg
    async def release_registration(self,m,t,e,s,g,cfg,excluded=None):
        try:member=await g.fetch_member(int(m['user']))
        except discord.NotFound:return
        excluded=set(excluded or [m['id']])
        event_ids={ev['id'] for ev in s['events'] if ev['guild']==e['guild']}
        others=[r for r in s['members'] if r['id'] not in excluded and r['user']==m['user'] and r['event'] in event_ids and r['status'] in ['approved','approving']]
        keep={team.get('role') for team in s['teams'] if any(r['team']==team['id'] for r in others)}
        role=g.get_role(int(t.get('role') or '0'))
        if role and str(role.id) not in keep:await member.remove_roles(role,reason='運営による大会登録解除')
        if not others and m['status'] in ['approved','approving']:
            await member.add_roles(g.get_role(int(cfg['unverified'])),reason='運営による大会登録解除')
            await member.remove_roles(g.get_role(int(cfg['verified'])),reason='運営による大会登録解除')
    async def execute(self,j,s):
        if j['kind'] in ['removeMember','deleteTeam']:
            m=next((m for m in s['members'] if m['id']==j['ref']),None) if j['kind']=='removeMember' else None
            t=next(t for t in s['teams'] if t['id']==(m['team'] if m else j['ref']));e=next(e for e in s['events'] if e['id']==t['event']);g,cfg=self.config(s,e['guild'])
            if m:
                await self.release_registration(m,t,e,s,g,cfg);return
            legacy=f"{t['name']} [{t['id'][:8]}]";label=team_label(t,s)
            role=g.get_role(int(t['role'])) if t.get('role') else discord.utils.get(g.roles,name=legacy)
            category=g.get_channel(int(t['category'])) if t.get('category') else discord.utils.get(g.categories,name=legacy)
            chat=g.get_channel(int(t['chat'])) if t.get('chat') else (discord.utils.get(category.text_channels,name=label.replace(' ','-').lower()) or discord.utils.get(category.text_channels,name='チームチャット')) if category else None
            vc=g.get_channel(int(t['vc'])) if t.get('vc') else (discord.utils.get(category.voice_channels,name=label) or discord.utils.get(category.voice_channels,name='チームVC')) if category else None
            for resource,cls in [(category,discord.CategoryChannel),(chat,discord.TextChannel),(vc,discord.VoiceChannel)]:
                if resource and not isinstance(resource,cls):raise ValueError('削除対象のチャンネル種類が一致しません。運営設定を確認してください。')
            ids={str(resource.id) for resource in [role,category,chat,vc] if resource}
            if any(team['id']!=t['id'] and team['status']!='deleted' and any(team.get(key) in ids for key in ['role','category','chat','vc']) for team in s['teams']):raise ValueError('他チームと共有するロール・チャンネルは削除できません。')
            if category and any(c.id not in {resource.id for resource in [chat,vc] if resource} for c in category.channels):raise ValueError('専用カテゴリに追加チャンネルがあります。移動または削除してから再試行してください。')
            if role and (role.is_default() or role.managed or role>=g.me.top_role):raise ValueError('チームロールをBotより下に置いてください。')
            members=[m for m in s['members'] if m['team']==t['id']];excluded={m['id'] for m in members}
            for member in members:await self.release_registration(member,t,e,s,g,cfg,excluded)
            for resource in [chat,vc,category,role]:
                if resource:
                    try:await resource.delete(reason='運営による大会チーム削除')
                    except discord.NotFound:pass
            return

        if j['kind'] in ['panel','changePanel']:
            e=next((e for e in s['events'] if e['id']==j['ref']),None)
            guild=e['guild'] if e else j['ref'];g,cfg=self.config(s,guild);r=(e or {}).get('registration',{})
            changes=j['kind']=='changePanel';channel=g.get_channel(int(r.get('changePanel') if changes else (r.get('panel') or cfg['panel'])))
            if not isinstance(channel,discord.TextChannel):raise ValueError('パネルのチャンネルが見つかりません。')
            title='メンバー変更・辞退' if changes else r.get('title','大会メンバー登録')
            description='本人がチーム変更・辞退を申請できます。運営承認後にロールと一覧に反映します。' if changes else r.get('description','チームコード → 個人情報 → 運営承認')
            marker=f"radius-panel:{j['ref']}:{j['kind']}"
            embed=discord.Embed(title=title,description=description);embed.set_footer(text=marker)
            view=Panel(e['id'] if e else None,changes)
            existing=None
            async for message in channel.history(limit=100):
                if message.author.id==self.user.id and message.embeds and message.embeds[0].footer.text==marker:existing=message;break
            if existing:await existing.edit(content=None,embed=embed,view=view)
            else:await channel.send(embed=embed,view=view)
            return
        if j['kind'] in ['changeReview','changeFeedback','applyChange']:
            c=next(c for c in s.get('changes',[]) if c['id']==j['ref']);m=next(m for m in s['members'] if m['id']==c['member']);t=next(t for t in s['teams'] if t['id']==m['team']);e=next(e for e in s['events'] if e['id']==c['event']);g,cfg=self.config(s,e['guild'])
            target=next((t for t in s['teams'] if t['id']==c.get('target')),None)
            if j['kind']=='changeReview':
                embed=discord.Embed(title={'correction':'登録情報の修正申請','transfer':'チーム変更申請','withdraw':'辞退申請'}[c['kind']])
                for k,v in [('大会',e['name']),('名前',m['name']),('Discord ID',m['user']),('チーム',t['name']),('申請理由',c['reason'])]:embed.add_field(name=k,value=discord.utils.escape_markdown(v)[:1024],inline=False)
                if target:embed.add_field(name='移動先',value=discord.utils.escape_markdown(target['name']))
                for k,v in (c.get('info') or {}).items():
                    if k=='tracker':continue
                    embed.add_field(name={'xid':'X ID','rank':'最高ランク','position':'参加区分','riotId':'Riot ID','displayName':'表示名（配信記載）'}.get(k,k),value=discord.utils.escape_markdown(dict((value,label) for label,value in POSITION_OPTIONS).get(v,v) if k=='position' else v),inline=False)
                view=discord.ui.View();view.add_item(discord.ui.Button(label='管理サイトで確認',url=SITE));await g.get_channel(int(cfg['review'])).send(embed=embed,view=view);return
            if j['kind']=='changeFeedback':
                try:
                    user=await self.fetch_user(int(m['user']));await user.send(f"{e['name']}：変更申請は{'差し戻し' if c['status']=='returned' else '否認'}です。\n理由：{c.get('reviewReason','')}\nDiscordのパネルから再申請してください。")
                except discord.HTTPException:pass
                return
            if c['kind']!='correction':
                try:member=await g.fetch_member(int(m['user']))
                except discord.NotFound:
                    if c['kind']!='withdraw':raise ValueError('対象メンバーがサーバーにいません。')
                    member=None
                others=[r for r in s['members'] if r['id']!=m['id'] and r['user']==m['user'] and r['status']=='approved' and any(ev['id']==r['event'] and ev['guild']==e['guild'] for ev in s['events'])]
                keep={team.get('role') for team in s['teams'] if any(r['team']==team['id'] for r in others)}
                if member:
                    if target:
                        role=g.get_role(int(target.get('role','0')))
                        if not role:raise ValueError('移動先のロールがありません。')
                        await member.add_roles(role,reason='大会チーム変更承認');keep.add(str(role.id))
                    role=g.get_role(int(t.get('role','0')))
                    if role and str(role.id) not in keep:await member.remove_roles(role,reason='大会変更・辞退承認')
                    if c['kind']=='withdraw' and not others:
                        await member.add_roles(g.get_role(int(cfg['unverified'])),reason='大会辞退承認');await member.remove_roles(g.get_role(int(cfg['verified'])),reason='大会辞退承認')
            try:
                user=await self.fetch_user(int(m['user']));await user.send(f"{e['name']}：申請が承認されました。")
            except discord.HTTPException:pass
            return
        if j['kind']=='team':
            t=next(t for t in s['teams'] if t['id']==j['ref']);e=next(e for e in s['events'] if e['id']==t['event']);g,cfg=self.config(s,e['guild'])
            marker=t['id'][:8];legacy=f"{t['name']} [{marker}]";label=team_label(t,s)
            role=g.get_role(int(t['role'])) if t.get('role') else discord.utils.get(g.roles,name=legacy)
            if not role:role=await g.create_role(name=legacy,reason='大会チーム作成')
            await api('progress',id=j['id'],role=str(role.id))
            if role.name!=label:await role.edit(name=label,reason='大会チーム名を更新')
            category=g.get_channel(int(t['category'])) if t.get('category') else discord.utils.get(g.categories,name=legacy)
            if not category:
                overwrites={g.default_role:discord.PermissionOverwrite(view_channel=False),role:discord.PermissionOverwrite(view_channel=True,send_messages=True,connect=True,speak=True),g.me:discord.PermissionOverwrite(view_channel=True,manage_channels=True,send_messages=True)}
                category=await g.create_category(legacy,overwrites=overwrites)
            await api('progress',id=j['id'],category=str(category.id))
            if category.name!=label:await category.edit(name=label,reason='大会チーム名を更新')
            chat=g.get_channel(int(t['chat'])) if t.get('chat') else discord.utils.get(category.text_channels,name=label.replace(' ','-').lower()) or discord.utils.get(category.text_channels,name='チームチャット')
            if not chat:chat=await g.create_text_channel(label,category=category)
            await api('progress',id=j['id'],chat=str(chat.id))
            if chat.name!=label:await chat.edit(name=label,reason='大会チーム名を更新')
            vc=g.get_channel(int(t['vc'])) if t.get('vc') else discord.utils.get(category.voice_channels,name=label) or discord.utils.get(category.voice_channels,name='チームVC')
            if not vc:vc=await g.create_voice_channel(label,category=category)
            await api('progress',id=j['id'],vc=str(vc.id))
            if vc.name!=label:await vc.edit(name=label,reason='大会チーム名を更新')
            return
        m=next(m for m in s['members'] if m['id']==j['ref']);t=next(t for t in s['teams'] if t['id']==m['team']);e=next(e for e in s['events'] if e['id']==m['event']);g,cfg=self.config(s,e['guild'])
        if j['kind']=='feedback':
            try:
                user=await self.fetch_user(int(m['user']));await user.send(f"{e['name']}：登録申請が差し戻されました。\n理由：{m.get('reason','')}\n登録パネルの「修正・再申請」から修正してください。")
            except discord.HTTPException:pass
            return
        if j['kind']=='review':
            embed=discord.Embed(title='メンバー登録申請',color=0x175be5)
            for k,v in [('チーム',t['name']),('名前',m['name']),('X ID','@'+m['xid']),('Discord ID',m['user']),('Riot ID',riot_id(m) or '未設定'),('表示名（配信記載）',m.get('displayName') or m['name']),('最高ランク',m['rank']),('参加区分',dict((value,label) for label,value in POSITION_OPTIONS).get(m.get('position','player'),'選手'))]:embed.add_field(name={'position':'参加区分','riotId':'Riot ID','displayName':'表示名（配信記載）'}.get(k,k),value=discord.utils.escape_markdown(dict((value,label) for label,value in POSITION_OPTIONS).get(v,v) if k=='position' else v),inline=False)
            view=discord.ui.View();view.add_item(discord.ui.Button(label='管理サイトで承認',url=SITE))
            await g.get_channel(int(cfg['review'])).send(embed=embed,view=view);return
        if j['kind']=='approve':
            member=await g.fetch_member(int(m['user']));roles=[g.get_role(int(cfg['verified'])),g.get_role(int(t.get('role','0')))]
            if any(r is None for r in roles):raise ValueError('認証済み、またはチームロールが見つかりません。')
            await member.add_roles(*roles,reason='大会登録承認');await member.remove_roles(g.get_role(int(cfg['unverified'])),reason='大会登録承認')
            try:await member.send(f"{e['name']} / {t['name']}：登録が承認されました。")
            except discord.HTTPException:pass
bot=Bot()
if __name__=='__main__':
    if not SITE or not KEY or not SERVICE:raise SystemExit('サイトから接続設定をダウンロードし、connection.envとして同じフォルダに置いてください。')
    if not os.getenv('DISCORD_TOKEN'):raise SystemExit('connection.envのDISCORD_TOKENにBotトークンを設定してください。')
    bot.run(os.environ['DISCORD_TOKEN'])
