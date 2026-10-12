import ast,asyncio,types,unittest
from pathlib import Path
from unittest.mock import AsyncMock
source=ast.parse(Path('public/bridge/bot.py').read_text())
method=next(n for n in next(n for n in source.body if isinstance(n,ast.ClassDef) and n.name=='Bot').body if isinstance(n,ast.AsyncFunctionDef) and n.name=='execute')
class HTTPException(Exception):pass
class NotFound(HTTPException):pass
scope={'discord':types.SimpleNamespace(HTTPException=HTTPException,NotFound=NotFound)}
exec(compile(ast.Module(body=[method],type_ignores=[]),'bot.execute','exec'),scope)
class Roles(unittest.IsolatedAsyncioTestCase):
    def setup_data(self,kind,others=False):
        roles={1:types.SimpleNamespace(id=1),2:types.SimpleNamespace(id=2),3:types.SimpleNamespace(id=3),4:types.SimpleNamespace(id=4)}
        self.member=types.SimpleNamespace(add_roles=AsyncMock(),remove_roles=AsyncMock())
        self.g=types.SimpleNamespace(get_role=lambda n:roles.get(n),fetch_member=AsyncMock(return_value=self.member))
        self.self=types.SimpleNamespace(config=lambda s,g:(self.g,{'verified':'3','unverified':'4'}),fetch_user=AsyncMock(return_value=types.SimpleNamespace(send=AsyncMock())))
        s={'events':[{'id':'e','guild':'g','name':'Cup'}], 'teams':[{'id':'a','role':'1'},{'id':'b','role':'2'}], 'members':[{'id':'m','team':'a','event':'e','user':'100','name':'A','status':'approved'}], 'changes':[{'id':'c','member':'m','event':'e','kind':kind,'status':'applying','target':'b' if kind=='transfer' else None}]}
        if others:s['members'].append({'id':'other','team':'a','event':'e','user':'100','status':'approved'})
        return s
    async def test_transfer(self):
        s=self.setup_data('transfer');await scope['execute'](self.self,{'kind':'applyChange','ref':'c'},s)
        self.member.add_roles.assert_awaited_once();self.assertEqual(self.member.add_roles.call_args.args[0].id,2);self.assertEqual(self.member.remove_roles.call_args.args[0].id,1)
    async def test_withdraw(self):
        s=self.setup_data('withdraw');await scope['execute'](self.self,{'kind':'applyChange','ref':'c'},s)
        self.assertEqual(self.member.remove_roles.await_count,2);self.assertEqual(self.member.add_roles.call_args.args[0].id,4)
    async def test_other_registration_keeps_shared_roles(self):
        s=self.setup_data('withdraw',True);await scope['execute'](self.self,{'kind':'applyChange','ref':'c'},s)
        self.member.remove_roles.assert_not_awaited();self.member.add_roles.assert_not_awaited()
    async def test_correction_has_no_role_mutation(self):
        s=self.setup_data('correction');await scope['execute'](self.self,{'kind':'applyChange','ref':'c'},s)
        self.member.remove_roles.assert_not_awaited();self.member.add_roles.assert_not_awaited()
    async def test_withdraw_absent_member(self):
        s=self.setup_data('withdraw');self.g.fetch_member.side_effect=NotFound();await scope['execute'](self.self,{'kind':'applyChange','ref':'c'},s)
        self.member.remove_roles.assert_not_awaited()
if __name__=='__main__':unittest.main()
