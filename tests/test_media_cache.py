import unittest
import test_listening as helpers
from test_platform import legacy


class MediaCacheTests(unittest.TestCase):
    setUp=helpers.ListeningTests.setUp
    tearDown=helpers.ListeningTests.tearDown
    post=helpers.ListeningTests.post
    audio=helpers.ListeningTests.audio

    def test_private_and_revoked_audio_never_cache(self):
        asset=self.audio(False);public=legacy.app.test_client()
        with self.c.get(asset['url']) as response:
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.headers['Cache-Control'],'no-store')
            etag=response.headers.get('ETag')
        response=public.get(asset['url']);self.assertEqual(response.status_code,404);self.assertEqual(response.headers['Cache-Control'],'no-store')
        self.post('/api/platform/admin/media/'+asset['id'],{'published':True})
        with public.get(asset['url']) as response:
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.headers['Cache-Control'],'no-store')
        self.post('/api/platform/admin/media/'+asset['id'],{'published':False})
        with public.get(asset['url'],headers={'If-None-Match':etag or ''}) as response:
            self.assertEqual(response.status_code,404)
            self.assertEqual(response.headers['Cache-Control'],'no-store')
        with self.c.get(asset['url'],headers={'Range':'bytes=0-15'}) as response:
            self.assertEqual(response.status_code,206)
            self.assertEqual(response.headers['Cache-Control'],'no-store')
