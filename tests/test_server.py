import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from duckpi.server import make_handler
DEMO=Path(__file__).resolve().parents[1]/'tests'/'fixtures'/'synthetic'
class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler());cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def request(self,path='/',payload=None,headers=None):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port);c.request('POST' if payload is not None else 'GET',path,body=payload,headers=headers or {})
        r=c.getresponse();result=(r.status,r.read());c.close();return result
    def test_page(self):
        status,body=self.request();self.assertEqual(status,200);self.assertIn(b'Pedigree review',body)
    def test_analysis_and_input_validation(self):
        p={name:(DEMO/f'{name if name!="metadata" else "metadata"}.tsv').read_text() for name in ['pairs','metadata','recorded']}
        p['method']='KING';status,body=self.request('/api/analyze',json.dumps(p))
        self.assertEqual(status,200);self.assertEqual(json.loads(body)['summary']['ambiguousRoles'],1)
        p['metadata']='broken';self.assertEqual(self.request('/api/analyze',json.dumps(p))[0],400)
    def test_origin_and_host(self):
        self.assertEqual(self.request(headers={'Host':'evil.test'})[0],403)
        self.assertEqual(self.request('/api/analyze','{}',{'Origin':'http://evil.test'})[0],403)
    def test_bad_routes_and_json(self):
        self.assertEqual(self.request('/secret')[0],404);self.assertEqual(self.request('/api/analyze','{')[0],400)
if __name__=='__main__':unittest.main()
