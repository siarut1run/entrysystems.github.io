import ast,sys,types,unittest
from pathlib import Path
from unittest.mock import AsyncMock,MagicMock
import discord
source=ast.parse(Path('public/bridge/bot.py').read_text())
helper=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='team_label')
method=next(n for n in next(n for n in source.body if isinstance(n,ast.ClassDef) and n.name=='Bot').body if isinstance(n,ast.AsyncFunctionDef) and n.name=='execute')
scope={'discord':discord}
exec(compile(ast.Module(body=[helper,method],type_ignores=[]),'bot.team','exec'),scope)
def obj(id,name):
    o=MagicMock();o.id=id;o.name=name
    async def edit(**kw):o.name=kw['name'];return o
    o.edit=AsyncMock(side_effect=edit);return o
class TeamNames(unittest.IsolatedAsyncioTestCase):
    async def test_create_and_retry_no_duplicates(self):
        t={'id':'abcdefgh-123','event':'e','name':'運営','number':1};s={'events':[{'id':'e','guild':'g'}],'teams':[t]};channels={};roles={}
        g=MagicMock();g.get_role=lambda n:roles.get(n);g.get_channel=lambda n:channels.get(n);g.roles=[];g.categories=[]
        async def create_role(**kw):r=obj(11,kw['name']);roles[11]=r;g.roles.append(r);return r
        async def create_category(name,**kw):c=obj(12,name);c.text_channels=[];c.voice_channels=[];channels[12]=c;g.categories.append(c);return c
        async def create_text(name,**kw):c=obj(13,name);channels[13]=c;kw['category'].text_channels.append(c);return c
        async def create_voice(name,**kw):c=obj(14,name);channels[14]=c;kw['category'].voice_channels.append(c);return c
        g.create_role=AsyncMock(side_effect=create_role);g.create_category=AsyncMock(side_effect=create_category);g.create_text_channel=AsyncMock(side_effect=create_text);g.create_voice_channel=AsyncMock(side_effect=create_voice)
        async def api(action,**kw):
            for k in ['role','category','chat','vc']:
                if k in kw:t[k]=kw[k]
        scope['api']=api;bot=types.SimpleNamespace(config=lambda s,guild:(g,{}));job={'kind':'team','ref':t['id'],'id':'j'}
        await scope['execute'](bot,job,s)
        self.assertEqual([roles[11].name]+[channels[n].name for n in [12,13,14]],['01_運営']*4)
        await scope['execute'](bot,job,s)
        for f in [g.create_role,g.create_category,g.create_text_channel,g.create_voice_channel]:f.assert_awaited_once()
    async def test_numbers(self):
        s={'teams':[{'id':'a','event':'e','name':'A'},{'id':'b','event':'e','name':'B'},{'id':'c','event':'f','name':'C'}]}
        self.assertEqual(scope['team_label'](s['teams'][1],s),'02_B');self.assertEqual(scope['team_label'](s['teams'][2],s),'01_C')
        self.assertEqual(scope['team_label']({'number':100,'name':'A'},s),'100_A')
if __name__=='__main__':unittest.main()
