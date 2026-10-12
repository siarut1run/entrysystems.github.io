import ast,asyncio,sys,unittest,types
from pathlib import Path
from unittest.mock import AsyncMock
from urllib.parse import unquote,urlparse
import discord
source=ast.parse(Path('public/bridge/bot.py').read_text())
selected=[n for n in source.body if (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ['RANK_OPTIONS','POSITION_OPTIONS'] for t in n.targets)) or (isinstance(n,ast.FunctionDef) and n.name=='riot_id') or (isinstance(n,ast.ClassDef) and n.name=='Info')]
scope={'discord':discord,'unquote':unquote,'urlparse':urlparse,'api':AsyncMock(),'reply_error':AsyncMock()}
exec(compile(ast.Module(body=selected,type_ignores=[]),'bot.Info','exec'),scope)
class RankSelect(unittest.IsolatedAsyncioTestCase):
    async def test_modal_payload(self):
        modal=scope['Info']('team',123)
        payload=modal.to_dict()
        self.assertEqual(len(payload['components']),5)
        self.assertEqual([c['label'] for c in payload['components']],['X ID','Riot ID','表示名（配信記載）','最高ランク','参加区分'])
        for c in payload['components']:self.assertEqual(c['type'],18)
        rank=payload['components'][3]['component']
        self.assertEqual(rank['type'],3);self.assertEqual(len(rank['options']),25)
        self.assertEqual(rank['options'][0]['label'],'IRON 1');self.assertEqual(rank['options'][-1]['label'],'RADIANT')
        self.assertEqual(len({o['value'] for o in rank['options']}),25);self.assertTrue(rank['required'])
        position=payload['components'][4];self.assertEqual(position['label'],'参加区分');self.assertEqual([o['label'] for o in position['component']['options']],['選手','コーチ','リザーブ']);self.assertTrue(position['component']['required'])
    async def test_correction_default(self):
        modal=scope['Info']('team',123,'event','correction',{'xid':'example','riotId':'Ruchiru#JP1','displayName':'配信用るちる','rank':'ASCENDANT 2','position':'reserve'})
        self.assertEqual([o.value for o in modal.rank.options if o.default],['ASCENDANT 2']);self.assertEqual([o.value for o in modal.position.options if o.default],['reserve']);self.assertEqual(str(modal.riotId),'Ruchiru#JP1');self.assertEqual(str(modal.displayName),'配信用るちる')
    async def test_submit_selected_value(self):
        modal=scope['Info']('team',123)
        modal.riotId._value='Ruchiru#JP1';modal.displayName._value='配信用名';modal.rank._values=['RADIANT'];modal.position._values=['coach']
        i=types.SimpleNamespace(user=types.SimpleNamespace(id=123,display_name='Name'),guild_id=456,response=types.SimpleNamespace(defer=AsyncMock()),followup=types.SimpleNamespace(send=AsyncMock()))
        scope['api'].reset_mock();await modal.on_submit(i)
        self.assertEqual(scope['api'].call_args.kwargs['rank'],'RADIANT');self.assertEqual(scope['api'].call_args.kwargs['position'],'coach');self.assertEqual(scope['api'].call_args.kwargs['riotId'],'Ruchiru#JP1');self.assertEqual(scope['api'].call_args.kwargs['displayName'],'配信用名');self.assertNotIn('tracker',scope['api'].call_args.kwargs)
    async def test_legacy_defaults(self):
        modal=scope['Info']('team',123,'event','correction',{'xid':'example','tracker':'https://tracker.gg/valorant/profile/riot/%E6%9C%88%E6%84%9B%23JP1/overview','name':'Discord名','rank':'GOLD 3'})
        self.assertEqual(str(modal.riotId),'月愛#JP1');self.assertEqual(str(modal.displayName),'Discord名')
    async def test_empty_selection_rejected(self):
        modal=scope['Info']('team',123)
        with self.assertRaises(ValueError):await modal.on_submit(types.SimpleNamespace(user=types.SimpleNamespace(id=123)))
if __name__=='__main__':unittest.main()
