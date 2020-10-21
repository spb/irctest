import re
from dataclasses import dataclass

from irctest import cases

from irctest.numerics import RPL_LUSERCLIENT, RPL_LUSEROP, RPL_LUSERUNKNOWN, RPL_LUSERCHANNELS, RPL_LUSERME, RPL_LOCALUSERS, RPL_GLOBALUSERS
from irctest.numerics import RPL_YOUREOPER

# 3 numbers, delimited by spaces, possibly negative (eek)
LUSERCLIENT_REGEX = re.compile(r'^.*( [-0-9]* ).*( [-0-9]* ).*( [-0-9]* ).*$')
# 2 numbers
LUSERME_REGEX = re.compile(r'^.*( [-0-9]* ).*( [-0-9]* ).*$')

@dataclass
class LusersResult:
    GlobalVisible: int = None
    GlobalInvisible: int = None
    Servers: int = None
    Opers: int = None
    Unregistered: int = None
    Channels: int = None
    LocalTotal: int = None
    LocalMax: int = None
    GlobalTotal: int = None
    GlobalMax: int = None

class LusersTestCase(cases.BaseServerTestCase):

    def getLusers(self, client):
        self.sendLine(client, 'LUSERS')
        messages = self.getMessages(client)
        by_numeric = dict((msg.command, msg) for msg in messages)

        result = LusersResult()

        # all of these take the nick as first param
        for message in messages:
            self.assertEqual(client, message.params[0])

        luserclient = by_numeric[RPL_LUSERCLIENT] # 251
        self.assertEqual(len(luserclient.params), 2)
        luserclient_param = luserclient.params[1]
        try:
            match = LUSERCLIENT_REGEX.match(luserclient_param)
            result.GlobalVisible = int(match.group(1))
            result.GlobalInvisible = int(match.group(2))
            result.Servers = int(match.group(3))
        except:
            raise ValueError("corrupt reply for 251 RPL_LUSERCLIENT", luserclient_param)

        result.Opers = int(by_numeric[RPL_LUSEROP].params[1])
        result.Unregistered = int(by_numeric[RPL_LUSERUNKNOWN].params[1])
        result.Channels = int(by_numeric[RPL_LUSERCHANNELS].params[1])
        localusers = by_numeric[RPL_LOCALUSERS]
        result.LocalTotal = int(localusers.params[1])
        result.LocalMax = int(localusers.params[2])
        globalusers = by_numeric[RPL_GLOBALUSERS]
        result.GlobalTotal = int(globalusers.params[1])
        result.GlobalMax = int(globalusers.params[2])

        luserme = by_numeric[RPL_LUSERME]
        self.assertEqual(len(luserme.params), 2)
        luserme_param = luserme.params[1]
        try:
            match = LUSERME_REGEX.match(luserme_param)
            localTotalFromUserme = int(match.group(1))
            serversFromUserme = int(match.group(2))
        except:
            raise ValueError("corrupt reply for 255 RPL_LUSERME", luserme_param)
        self.assertEqual(result.LocalTotal, localTotalFromUserme)
        # serversFromUserme is "servers i'm currently connected to", generally undefined
        self.assertGreaterEqual(serversFromUserme, 0)

        return result

class BasicLusersTest(LusersTestCase):

    @cases.SpecificationSelector.requiredBySpecification('RFC2812')
    def testLusers(self):
        self.connectClient('bar', name='bar')
        lusers = self.getLusers('bar')
        self.assertEqual(lusers.Unregistered, 0)
        self.assertEqual(lusers.GlobalTotal, 1)
        self.assertEqual(lusers.GlobalMax, 1)
        self.assertGreaterEqual(lusers.GlobalInvisible, 0)
        self.assertGreaterEqual(lusers.GlobalVisible, 0)
        self.assertEqual(lusers.GlobalInvisible + lusers.GlobalVisible, 1)
        self.assertEqual(lusers.LocalTotal, 1)
        self.assertEqual(lusers.LocalMax, 1)

        self.connectClient('qux', name='qux')
        lusers = self.getLusers('qux')
        self.assertEqual(lusers.Unregistered, 0)
        self.assertEqual(lusers.GlobalTotal, 2)
        self.assertEqual(lusers.GlobalMax, 2)
        self.assertGreaterEqual(lusers.GlobalInvisible, 0)
        self.assertGreaterEqual(lusers.GlobalVisible, 0)
        self.assertEqual(lusers.GlobalInvisible + lusers.GlobalVisible, 2)
        self.assertEqual(lusers.LocalTotal, 2)
        self.assertEqual(lusers.LocalMax, 2)

        self.sendLine('qux', 'QUIT')
        self.assertDisconnected('qux')
        lusers = self.getLusers('bar')
        self.assertEqual(lusers.Unregistered, 0)
        self.assertEqual(lusers.GlobalTotal, 1)
        self.assertEqual(lusers.GlobalMax, 2)
        self.assertGreaterEqual(lusers.GlobalInvisible, 0)
        self.assertGreaterEqual(lusers.GlobalVisible, 0)
        self.assertEqual(lusers.GlobalInvisible + lusers.GlobalVisible, 1)
        self.assertEqual(lusers.LocalTotal, 1)
        self.assertEqual(lusers.LocalMax, 2)


class LusersUnregisteredTestCase(LusersTestCase):

    @cases.SpecificationSelector.requiredBySpecification('RFC2812')
    def testLusers(self):
        self.connectClient('bar', name='bar')
        lusers = self.getLusers('bar')
        self.assertEqual(lusers.Unregistered, 0)
        self.assertEqual(lusers.GlobalTotal, 1)
        self.assertEqual(lusers.GlobalMax, 1)
        self.assertGreaterEqual(lusers.GlobalInvisible, 0)
        self.assertGreaterEqual(lusers.GlobalVisible, 0)
        self.assertEqual(lusers.GlobalInvisible + lusers.GlobalVisible, 1)
        self.assertEqual(lusers.LocalTotal, 1)
        self.assertEqual(lusers.LocalMax, 1)

        self.addClient('qux')
        self.sendLine('qux', 'NICK qux')
        self.getMessages('qux')
        lusers = self.getLusers('bar')
        self.assertEqual(lusers.Unregistered, 1)
        self.assertEqual(lusers.GlobalTotal, 1)
        self.assertEqual(lusers.GlobalMax, 1)
        self.assertGreaterEqual(lusers.GlobalInvisible, 0)
        self.assertGreaterEqual(lusers.GlobalVisible, 0)
        self.assertEqual(lusers.GlobalInvisible + lusers.GlobalVisible, 1)
        self.assertEqual(lusers.LocalTotal, 1)
        self.assertEqual(lusers.LocalMax, 1)

        self.addClient('bat')
        self.sendLine('bat', 'NICK bat')
        self.getMessages('bat')
        lusers = self.getLusers('bar')
        self.assertEqual(lusers.Unregistered, 2)
        self.assertEqual(lusers.GlobalTotal, 1)
        self.assertEqual(lusers.GlobalMax, 1)
        self.assertGreaterEqual(lusers.GlobalInvisible, 0)
        self.assertGreaterEqual(lusers.GlobalVisible, 0)
        self.assertEqual(lusers.GlobalInvisible + lusers.GlobalVisible, 1)
        self.assertEqual(lusers.LocalTotal, 1)
        self.assertEqual(lusers.LocalMax, 1)

        # complete registration on one client
        self.sendLine('qux', 'USER u s e r')
        self.getMessages('qux')
        lusers = self.getLusers('bar')
        self.assertEqual(lusers.Unregistered, 1)
        self.assertEqual(lusers.GlobalTotal, 2)
        self.assertEqual(lusers.GlobalMax, 2)
        self.assertGreaterEqual(lusers.GlobalInvisible, 0)
        self.assertGreaterEqual(lusers.GlobalVisible, 0)
        self.assertEqual(lusers.GlobalInvisible + lusers.GlobalVisible, 2)
        self.assertEqual(lusers.LocalTotal, 2)
        self.assertEqual(lusers.LocalMax, 2)

        # QUIT the other without registering
        self.sendLine('bat', 'QUIT')
        self.assertDisconnected('bat')
        lusers = self.getLusers('bar')
        self.assertEqual(lusers.Unregistered, 0)
        self.assertEqual(lusers.GlobalTotal, 2)
        self.assertEqual(lusers.GlobalMax, 2)
        self.assertGreaterEqual(lusers.GlobalInvisible, 0)
        self.assertGreaterEqual(lusers.GlobalVisible, 0)
        self.assertEqual(lusers.GlobalInvisible + lusers.GlobalVisible, 2)
        self.assertEqual(lusers.LocalTotal, 2)
        self.assertEqual(lusers.LocalMax, 2)


class LuserOpersTest(LusersTestCase):

    @cases.SpecificationSelector.requiredBySpecification('Oragono')
    def testLuserOpers(self):
        self.connectClient('bar', name='bar')
        lusers = self.getLusers('bar')
        self.assertEqual(lusers.GlobalTotal, 1)
        self.assertEqual(lusers.GlobalMax, 1)
        self.assertGreaterEqual(lusers.GlobalInvisible, 0)
        self.assertGreaterEqual(lusers.GlobalVisible, 0)
        self.assertEqual(lusers.GlobalInvisible + lusers.GlobalVisible, 1)
        self.assertEqual(lusers.LocalTotal, 1)
        self.assertEqual(lusers.LocalMax, 1)
        self.assertEqual(lusers.Opers, 0)

        # add 1 oper
        self.sendLine('bar', 'OPER root frenchfries')
        msgs = self.getMessages('bar')
        self.assertIn(RPL_YOUREOPER, {msg.command for msg in msgs})
        lusers = self.getLusers('bar')
        self.assertEqual(lusers.GlobalTotal, 1)
        self.assertEqual(lusers.GlobalMax, 1)
        self.assertGreaterEqual(lusers.GlobalInvisible, 0)
        self.assertGreaterEqual(lusers.GlobalVisible, 0)
        self.assertEqual(lusers.GlobalInvisible + lusers.GlobalVisible, 1)
        self.assertEqual(lusers.LocalTotal, 1)
        self.assertEqual(lusers.LocalMax, 1)
        self.assertEqual(lusers.Opers, 1)

        # now 2 opers
        self.connectClient('qux', name='qux')
        self.sendLine('qux', 'OPER root frenchfries')
        self.getMessages('qux')
        lusers = self.getLusers('bar')
        self.assertEqual(lusers.GlobalTotal, 2)
        self.assertEqual(lusers.GlobalMax, 2)
        self.assertGreaterEqual(lusers.GlobalInvisible, 0)
        self.assertGreaterEqual(lusers.GlobalVisible, 0)
        self.assertEqual(lusers.GlobalInvisible + lusers.GlobalVisible, 2)
        self.assertEqual(lusers.LocalTotal, 2)
        self.assertEqual(lusers.LocalMax, 2)
        self.assertEqual(lusers.Opers, 2)

        # remove oper with MODE
        self.sendLine('bar', 'MODE bar -o')
        msgs = self.getMessages('bar')
        self.assertIn('MODE', {msg.command for msg in msgs})
        lusers = self.getLusers('bar')
        self.assertEqual(lusers.GlobalTotal, 2)
        self.assertEqual(lusers.GlobalMax, 2)
        self.assertGreaterEqual(lusers.GlobalInvisible, 0)
        self.assertGreaterEqual(lusers.GlobalVisible, 0)
        self.assertEqual(lusers.GlobalInvisible + lusers.GlobalVisible, 2)
        self.assertEqual(lusers.LocalTotal, 2)
        self.assertEqual(lusers.LocalMax, 2)
        self.assertEqual(lusers.Opers, 1)

        # remove oper by quit
        self.sendLine('qux', 'QUIT')
        self.assertDisconnected('qux')
        lusers = self.getLusers('bar')
        self.assertEqual(lusers.GlobalTotal, 1)
        self.assertEqual(lusers.GlobalMax, 2)
        self.assertGreaterEqual(lusers.GlobalInvisible, 0)
        self.assertGreaterEqual(lusers.GlobalVisible, 0)
        self.assertEqual(lusers.GlobalInvisible + lusers.GlobalVisible, 1)
        self.assertEqual(lusers.LocalTotal, 1)
        self.assertEqual(lusers.LocalMax, 2)
        self.assertEqual(lusers.Opers, 0)


class OragonoInvisibleDefaultTest(LusersTestCase):

    def customizedConfig(self):
        conf = self.controller.baseConfig()
        conf['accounts']['default-user-modes'] = '+i'
        return conf

    @cases.SpecificationSelector.requiredBySpecification('Oragono')
    def testLusers(self):
        self.connectClient('bar', name='bar')
        lusers = self.getLusers('bar')
        self.assertEqual(lusers.GlobalTotal, 1)
        self.assertEqual(lusers.GlobalMax, 1)
        self.assertEqual(lusers.GlobalInvisible, 1)
        self.assertEqual(lusers.GlobalVisible, 0)
        self.assertEqual(lusers.LocalTotal, 1)
        self.assertEqual(lusers.LocalMax, 1)

        self.connectClient('qux', name='qux')
        lusers = self.getLusers('qux')
        self.assertEqual(lusers.GlobalTotal, 2)
        self.assertEqual(lusers.GlobalMax, 2)
        self.assertEqual(lusers.GlobalInvisible, 2)
        self.assertEqual(lusers.GlobalVisible, 0)
        self.assertEqual(lusers.LocalTotal, 2)
        self.assertEqual(lusers.LocalMax, 2)

        # remove +i with MODE
        self.sendLine('bar', 'MODE bar -i')
        msgs = self.getMessages('bar')
        lusers = self.getLusers('bar')
        self.assertIn('MODE', {msg.command for msg in msgs})
        self.assertEqual(lusers.GlobalTotal, 2)
        self.assertEqual(lusers.GlobalMax, 2)
        self.assertEqual(lusers.GlobalInvisible, 1)
        self.assertEqual(lusers.GlobalVisible, 1)
        self.assertEqual(lusers.LocalTotal, 2)
        self.assertEqual(lusers.LocalMax, 2)

        # disconnect invisible user
        self.sendLine('qux', 'QUIT')
        self.assertDisconnected('qux')
        lusers = self.getLusers('bar')
        self.assertEqual(lusers.GlobalTotal, 1)
        self.assertEqual(lusers.GlobalMax, 2)
        self.assertEqual(lusers.GlobalInvisible, 0)
        self.assertEqual(lusers.GlobalVisible, 1)
        self.assertEqual(lusers.LocalTotal, 1)
        self.assertEqual(lusers.LocalMax, 2)
