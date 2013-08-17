import os
import unittest
from datetime import datetime

from betamax import cassette
from requests.models import Response, Request
from requests.packages import urllib3
from requests.structures import CaseInsensitiveDict

from pytest import skip


def decode(s):
    if hasattr(s, 'decode'):
        return s.decode()
    return s


class TestSerialization(unittest.TestCase):

    """Unittests for the serialization and deserialization functions.

    This tests:

        - deserialize_prepared_request
        - deserialize_response
        - serialize_prepared_request
        - serialize_response

    """

    def test_serialize_response(self):
        r = Response()
        r.status_code = 200
        r.encoding = 'utf-8'
        r.headers = CaseInsensitiveDict()
        r.url = 'http://example.com'
        cassette.add_urllib3_response({'content': decode('foo')}, r)
        serialized = cassette.serialize_response(r, 'json')
        assert serialized is not None
        assert serialized != {}
        assert serialized['status_code'] == 200
        assert serialized['encoding'] == 'utf-8'
        assert serialized['content'] == 'foo'
        assert serialized['headers'] == {}
        assert serialized['url'] == 'http://example.com'

    def test_deserialize_response(self):
        s = {
            'content': decode('foo'),
            'encoding': 'utf-8',
            'headers': {
                'Content-Type': decode('application/json')
            },
            'url': 'http://example.com/',
            'status_code': 200,
            'recorded_at': '2013-08-31T00:00:01'
        }
        r = cassette.deserialize_response(s)
        assert r.content == b'foo'
        assert r.encoding == 'utf-8'
        assert r.headers == {'Content-Type': 'application/json'}
        assert r.url == 'http://example.com/'
        assert r.status_code == 200

    def test_serialize_prepared_request(self):
        r = Request()
        r.method = 'GET'
        r.url = 'http://example.com'
        r.headers = {'User-Agent': 'betamax/test header'}
        r.data = {'key': 'value'}
        p = r.prepare()
        serialized = cassette.serialize_prepared_request(p, 'json')
        assert serialized is not None
        assert serialized != {}
        assert serialized['method'] == 'GET'
        assert serialized['url'] == 'http://example.com/'
        assert serialized['headers'] == {
            'Content-Length': '9',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'betamax/test header',
        }
        assert serialized['body'] == 'key=value'

    def test_deserialize_prepared_request(self):
        s = {
            'body': 'key=value',
            'headers': {
                'User-Agent': 'betamax/test header',
            },
            'method': 'GET',
            'url': 'http://example.com/',
        }
        p = cassette.deserialize_prepared_request(s)
        assert p.body == 'key=value'
        assert p.headers == CaseInsensitiveDict(
            {'User-Agent': 'betamax/test header'}
        )
        assert p.method == 'GET'
        assert p.url == 'http://example.com/'

    def test_add_urllib3_response(self):
        r = Response()
        r.status_code = 200
        r.headers = {}
        cassette.add_urllib3_response({'content': decode('foo')}, r)
        assert isinstance(r.raw, urllib3.response.HTTPResponse)
        assert r.content == b'foo'
        assert isinstance(r.raw._original_response, cassette.MockHTTPResponse)


class TestCassette(unittest.TestCase):
    cassette_name = 'test_cassette.json'

    def setUp(self):
        self.cassette = cassette.Cassette(
            TestCassette.cassette_name,
            'json',
            'w+'
        )
        r = Response()
        r.status_code = 200
        r.encoding = 'utf-8'
        r.headers = CaseInsensitiveDict({'Content-Type': decode('foo')})
        r.url = 'http://example.com'
        cassette.add_urllib3_response({'content': decode('foo')}, r)
        self.response = r
        r = Request()
        r.method = 'GET'
        r.url = 'http://example.com'
        r.headers = {}
        r.data = {'key': 'value'}
        self.response.request = r.prepare()
        self.response.request.headers.update(
            {'User-Agent': 'betamax/test header'}
        )
        self.json = {
            'request': {
                'body': 'key=value',
                'headers': {
                    'User-Agent': 'betamax/test header',
                    'Content-Length': '9',
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                'method': 'GET',
                'url': 'http://example.com/',
            },
            'response': {
                'content': decode('foo'),
                'encoding': 'utf-8',
                'headers': {'Content-Type': decode('foo')},
                'status_code': 200,
                'url': 'http://example.com',
            },
            'recorded_at': '2013-08-31T00:00:00',
        }
        self.date = datetime(2013, 8, 31)

    def tearDown(self):
        if os.path.exists(TestCassette.cassette_name):
            os.unlink(TestCassette.cassette_name)

    @skip
    def test_serialize(self):
        serialized = self.cassette.serialize(self.response)
        assert serialized['request'] == self.json['request']
        assert serialized['response'] == self.json['response']
        assert serialized.get('recorded_at') is not None

    def test_holds_interactions(self):
        assert isinstance(self.cassette.interactions, list)
        assert self.cassette.interactions != []


class TestInteraction(unittest.TestCase):
    def setUp(self):
        self.request = {
            'body': 'key=value',
            'headers': {
                'User-Agent': 'betamax/test header',
                'Content-Length': '9',
                'Content-Type': 'application/x-www-form-urlencoded',
                },
            'method': 'GET',
            'url': 'http://example.com/',
        }
        self.response = {
            'content': decode('foo'),
            'encoding': 'utf-8',
            'headers': {'Content-Type': decode('foo')},
            'status_code': 200,
            'url': 'http://example.com',
        }
        self.json = {
            'request': self.request,
            'response': self.response,
            'recorded_at': '2013-08-31T00:00:00',
        }
        self.interaction = cassette.Interaction(self.json)
        self.date = datetime(2013, 8, 31)

    def test_as_response(self):
        r = self.interaction.as_response()
        assert isinstance(r, Response)

    def test_deserialized_response(self):
        r = self.interaction.as_response()
        for attr in ['status_code', 'encoding', 'content', 'headers', 'url']:
            assert getattr(self.response, attr) == getattr(r, attr)
        actual_req = r.request
        expected_req = self.response.request
        for attr in ['method', 'url', 'headers', 'body']:
            assert getattr(expected_req, attr) == getattr(actual_req, attr)

        assert self.date == self.cassette.recorded_at
