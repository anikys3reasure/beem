from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import super
import unittest
from parameterized import parameterized
from pprint import pprint
from beem import Steem, exceptions
from beem.comment import Comment, RecentReplies, RecentByPath
from beem.vote import Vote
from beem.instance import set_shared_steem_instance
from beem.utils import resolve_authorperm
from beem.nodelist import NodeList

wif = "5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtP79zkvFD3"


class Testcases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        nodelist = NodeList()
        cls.bts = Steem(
            node=nodelist.get_nodes(appbase=False),
            use_condenser=True,
            nobroadcast=True,
            unsigned=True,
            keys={"active": wif},
            num_retries=10
        )
        cls.appbase = Steem(
            node=nodelist.get_nodes(normal=False, appbase=True),
            nobroadcast=True,
            unsigned=True,
            keys={"active": wif},
            num_retries=10
        )
        cls.authorperm = "@gtg/ffdhu-gtg-witness-log"
        [author, permlink] = resolve_authorperm(cls.authorperm)
        cls.author = author
        cls.permlink = permlink
        cls.category = 'witness-category'
        cls.title = 'gtg witness log'
        # from getpass import getpass
        # self.bts.wallet.unlock(getpass())
        # set_shared_steem_instance(cls.bts)
        # cls.bts.set_default_account("test")

    @parameterized.expand([
        ("non_appbase"),
        ("appbase"),
    ])
    def test_comment(self, node_param):
        if node_param == "non_appbase":
            bts = self.bts
        else:
            bts = self.appbase
        with self.assertRaises(
            exceptions.ContentDoesNotExistsException
        ):
            Comment("@abcdef/abcdef", steem_instance=bts)
        c = Comment(self.authorperm, steem_instance=bts)
        self.assertTrue(isinstance(c.id, int))
        self.assertTrue(c.id > 0)
        self.assertEqual(c.author, self.author)
        self.assertEqual(c.permlink, self.permlink)
        self.assertEqual(c.authorperm, self.authorperm)
        self.assertEqual(c.category, self.category)
        self.assertEqual(c.parent_author, '')
        self.assertEqual(c.parent_permlink, self.category)
        self.assertEqual(c.title, self.title)
        self.assertTrue(len(c.body) > 0)
        for key in ['tags', 'users', 'image', 'links', 'app', 'format']:
            self.assertIn(key, list(c.json_metadata.keys()))
        self.assertTrue(c.is_main_post())
        self.assertFalse(c.is_comment())
        self.assertFalse(c.is_pending())
        self.assertTrue((c.time_elapsed().total_seconds() / 60 / 60 / 24) > 7.0)
        self.assertTrue(isinstance(c.get_reblogged_by(), list))
        self.assertTrue(len(c.get_reblogged_by()) > 0)
        self.assertTrue(isinstance(c.get_votes(), list))
        if node_param == "appbase":
            self.assertTrue(len(c.get_votes()) > 0)
            self.assertTrue(isinstance(c.get_votes()[0], Vote))

    @parameterized.expand([
        ("non_appbase"),
        ("appbase"),
    ])
    def test_comment_dict(self, node_param):
        if node_param == "non_appbase":
            bts = self.bts
        else:
            bts = self.appbase
        c = Comment({'author': self.author, 'permlink': self.permlink}, steem_instance=bts)
        c.refresh()
        self.assertEqual(c.author, self.author)
        self.assertEqual(c.permlink, self.permlink)
        self.assertEqual(c.authorperm, self.authorperm)
        self.assertEqual(c.category, self.category)
        self.assertEqual(c.parent_author, '')
        self.assertEqual(c.parent_permlink, self.category)
        self.assertEqual(c.title, self.title)

    @parameterized.expand([
        ("non_appbase"),
        ("appbase"),
    ])
    def test_vote(self, node_param):
        if node_param == "non_appbase":
            bts = self.bts
        else:
            bts = self.appbase
        c = Comment(self.authorperm, steem_instance=bts)
        bts.txbuffer.clear()
        tx = c.vote(100, account="test")
        self.assertEqual(
            (tx["operations"][0][0]),
            "vote"
        )
        op = tx["operations"][0][1]
        self.assertIn(
            "test",
            op["voter"])
        c.steem.txbuffer.clear()
        tx = c.upvote(weight=150, voter="test")
        op = tx["operations"][0][1]
        self.assertEqual(op["weight"], 10000)
        c.steem.txbuffer.clear()
        tx = c.upvote(weight=99.9, voter="test")
        op = tx["operations"][0][1]
        self.assertEqual(op["weight"], 9990)
        c.steem.txbuffer.clear()
        tx = c.downvote(weight=-150, voter="test")
        op = tx["operations"][0][1]
        self.assertEqual(op["weight"], -10000)
        c.steem.txbuffer.clear()
        tx = c.downvote(weight=-99.9, voter="test")
        op = tx["operations"][0][1]
        self.assertEqual(op["weight"], -9990)

    @parameterized.expand([
        ("non_appbase"),
        ("appbase"),
    ])
    def test_export(self, node_param):
        if node_param == "non_appbase":
            bts = self.bts
        else:
            bts = self.appbase

        if bts.rpc.get_use_appbase():
            content = bts.rpc.get_discussion({'author': self.author, 'permlink': self.permlink}, api="tags")
        else:
            content = bts.rpc.get_content(self.author, self.permlink)

        c = Comment(self.authorperm, steem_instance=bts)
        keys = list(content.keys())
        json_content = c.json()

        for k in keys:
            if k not in "json_metadata" and k != 'reputation' and k != 'active_votes':
                self.assertEqual(content[k], json_content[k])

    def test_resteem(self):
        bts = self.bts
        bts.txbuffer.clear()
        c = Comment(self.authorperm, steem_instance=bts)
        tx = c.resteem(account="test")
        self.assertEqual(
            (tx["operations"][0][0]),
            "custom_json"
        )

    def test_reply(self):
        bts = self.bts
        bts.txbuffer.clear()
        c = Comment(self.authorperm, steem_instance=bts)
        tx = c.reply(body="Good post!", author="test")
        self.assertEqual(
            (tx["operations"][0][0]),
            "comment"
        )
        op = tx["operations"][0][1]
        self.assertIn(
            "test",
            op["author"])

    def test_delete(self):
        bts = self.bts
        bts.txbuffer.clear()
        c = Comment(self.authorperm, steem_instance=bts)
        tx = c.delete(account="test")
        self.assertEqual(
            (tx["operations"][0][0]),
            "delete_comment"
        )
        op = tx["operations"][0][1]
        self.assertIn(
            self.author,
            op["author"])

    def test_edit(self):
        bts = self.bts
        bts.txbuffer.clear()
        c = Comment(self.authorperm, steem_instance=bts)
        c.edit(c.body, replace=False)
        body = c.body + "test"
        tx = c.edit(body, replace=False)
        self.assertEqual(
            (tx["operations"][0][0]),
            "comment"
        )
        op = tx["operations"][0][1]
        self.assertIn(
            self.author,
            op["author"])

    def test_edit_replace(self):
        bts = self.bts
        bts.txbuffer.clear()
        c = Comment(self.authorperm, steem_instance=bts)
        body = c.body + "test"
        tx = c.edit(body, meta=c["json_metadata"], replace=True)
        self.assertEqual(
            (tx["operations"][0][0]),
            "comment"
        )
        op = tx["operations"][0][1]
        self.assertIn(
            self.author,
            op["author"])
        self.assertEqual(body, op["body"])

    def test_recent_replies(self):
        bts = self.bts
        r = RecentReplies(self.author, skip_own=True, steem_instance=bts)
        self.assertTrue(len(r) > 0)
        self.assertTrue(r[0] is not None)

    def test_recent_by_path(self):
        bts = self.bts
        r = RecentByPath(category="hot", steem_instance=bts)
        self.assertTrue(len(r) > 0)
        self.assertTrue(r[0] is not None)
