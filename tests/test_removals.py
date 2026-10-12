import ast,types,unittest
from pathlib import Path
from unittest.mock import AsyncMock,MagicMock
import discord
source=ast.parse(Path('public/bridge/bot.py').read_text());bot=next(n for n in source.body if isinstance(n,ast.ClassDef) and n.name=='Bot')
methods=[n for n in bot.body if isinstance(n,ast.AsyncFunctionDef) and n.name in ['execute','release_registration']]
helper=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='team_label')
scope={'discord':discord};exec(compile(ast.Module(body=[helper,*methods],type_ignores=[]),'bot.removals','exec'),scope)
class Removals(unittest.IsolatedAsyncioTestCase):
    def data(self,other=False):
        role=MagicMock(spec=discord.Role);role.id=11;role.is_default.return_value=False;role.managed=False;role.__ge__.return_value=False;role.delete=AsyncMock()
        verified=MagicMock(spec=discord.Role);verified.id=21
        unverified=MagicMock(spec=discord.Role);unverified.id=22
        category=MagicMock(spec=discord.CategoryChannel);category.id=12;category.delete=AsyncMock()
        chat=MagicMock(spec=discord.TextChannel);chat.id=13;chat.delete=AsyncMock()
        vc=MagicMock(spec=discord.VoiceChannel);vc.id=14;vc.delete=AsyncMock();category.channels=[chat,vc]
        roles={11:role,21:verified,22:unverified};channels={12:category,13:chat,14:vc}
        self.member=types.SimpleNamespace(add_roles=AsyncMock(),remove_roles=AsyncMock());self.g=types.SimpleNamespace(get_role=lambda n:roles.get(n),get_channel=lambda n:channels.get(n),fetch_member=AsyncMock(return_value=self.member),me=MagicMock())
        self.bot=types.SimpleNamespace(config=lambda s,g:(self.g,{'verified':'21','unverified':'22'}));self.bot.release_registration=types.MethodType(scope['release_registration'],self.bot)
        s={'events':[{'id':'e','guild':'g','name':'Cup'}], 'teams':[{'id':'t','name':'A','number':1,'event':'e','status':'deleting','role':'11','category':'12','chat':'13','vc':'14'}], 'members':[{'id':'m','team':'t','event':'e','user':'100','status':'approved','removing':True}]}
        if other:
            s['teams'].append({'id':'other','event':'e','name':'Other','status':'ready','role':'31'})
            s['members'].append({'id':'other-m','team':'other','event':'e','user':'100','status':'approved'})
        return s,(role,category,chat,vc)
    async def test_member_removal(self):
        s,resources=self.data();await scope['execute'](self.bot,{'kind':'removeMember','ref':'m'},s)
        self.assertEqual(self.member.remove_roles.await_count,2);self.assertEqual(self.member.add_roles.call_args.args[0].id,22)
        for r in resources:r.delete.assert_not_awaited()
    async def test_common_role_kept_for_other_entry(self):
        s,_=self.data(True);await scope['execute'](self.bot,{'kind':'removeMember','ref':'m'},s)
        self.assertEqual(self.member.remove_roles.await_count,1);self.member.add_roles.assert_not_awaited()
    async def test_delete_resources(self):
        s,resources=self.data();await scope['execute'](self.bot,{'kind':'deleteTeam','ref':'t'},s)
        for r in resources:r.delete.assert_awaited_once()
        self.assertEqual(self.member.remove_roles.await_count,2)
    async def test_deleted_resource_is_idempotent(self):
        s,resources=self.data();resources[2].delete.side_effect=discord.NotFound(types.SimpleNamespace(status=404,reason='Not Found'),'missing')
        await scope['execute'](self.bot,{'kind':'deleteTeam','ref':'t'},s)
        resources[0].delete.assert_awaited_once();resources[1].delete.assert_awaited_once()
    async def test_additional_channel_blocks_deletion(self):
        s,resources=self.data();extra=MagicMock(spec=discord.TextChannel);extra.id=99;resources[1].channels.append(extra)
        with self.assertRaises(ValueError):await scope['execute'](self.bot,{'kind':'deleteTeam','ref':'t'},s)
        for r in resources:r.delete.assert_not_awaited()
        self.member.remove_roles.assert_not_awaited()
    async def test_pending_entry_preserves_common_role(self):
        s,_=self.data();s['members'][0]['status']='pending';await scope['execute'](self.bot,{'kind':'removeMember','ref':'m'},s)
        self.assertEqual(self.member.remove_roles.await_count,1);self.member.add_roles.assert_not_awaited()
if __name__=='__main__':unittest.main()
