import io,json,os,sqlite3,subprocess,tempfile,unittest,zipfile
from functools import lru_cache
from pathlib import Path
from unittest.mock import patch
import imageio_ffmpeg
import test_listening as helpers
from test_platform import legacy
from video_media import clean_video
from scripts.restore_backup import restore


@lru_cache(maxsize=3)
def synthetic_video(audio=False,codec='libx264'):
    with tempfile.TemporaryDirectory(prefix='thana-video-fixture-') as folder:
        path=Path(folder)/'fixture.mp4'
        args=[imageio_ffmpeg.get_ffmpeg_exe(),'-nostdin','-v','error','-f','lavfi','-i','color=c=blue:s=64x64:r=10:d=1']
        if audio:args+=['-f','lavfi','-i','anullsrc=channel_layout=mono:sample_rate=16000','-c:a','aac']
        args+=['-t','1','-c:v',codec,'-threads','1','-pix_fmt','yuv420p','-metadata','title=fixture_private_metadata','-movflags','+faststart',str(path)]
        subprocess.run(args,check=True,timeout=15,capture_output=True)
        return path.read_bytes()


class VideoMediaTests(unittest.TestCase):
    post=helpers.ListeningTests.post
    audio=helpers.ListeningTests.audio
    def setUp(self):helpers.ListeningTests.setUp(self);self.courses=[];self.lessons=[]
    def tearDown(self):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            for lid in self.lessons:c.execute('DELETE FROM course_lessons WHERE id=?',(lid,));c.execute('DELETE FROM lesson_revisions WHERE lesson=?',(lid,))
            for cid in self.courses:c.execute('DELETE FROM courses WHERE id=?',(cid,))
        helpers.ListeningTests.tearDown(self)
    def upload(self,raw):
        token=self.c.get('/api/csrf').json['token']
        return self.c.post('/api/platform/admin/media',data={'file':(io.BytesIO(raw),'fixture.mp4'),'title':'Synthetic blue clip'},headers={'X-CSRF-Token':token})

    def test_video_upload_publication_range_and_lesson(self):
        uploaded=self.upload(synthetic_video());self.assertEqual(uploaded.status_code,201,uploaded.json)
        asset=uploaded.json;self.assets.append(asset['id'])
        self.assertEqual(legacy.app.test_client().get(asset['url']).status_code,404)
        with self.c.get(asset['url']) as response:
            self.assertEqual(response.mimetype,'video/mp4');self.assertEqual(response.headers['Cache-Control'],'no-store');self.assertNotIn(b'fixture_private_metadata',response.data)
        cid=self.post('/api/platform/admin/courses',{'title':'Synthetic video course','language':'ko'}).json['id'];self.courses.append(cid)
        content={'title':'Synthetic video lesson','blocks':[{'type':'video','value':asset['url']}],'quiz':[]}
        r=self.post('/api/platform/admin/courses/'+cid+'/lessons',content);self.assertEqual(r.status_code,201,r.json);lid=r.json['id'];self.lessons.append(lid)
        self.assertEqual(self.post('/api/platform/admin/lessons/'+lid,{'revision':1,'action':'publish','content':content}).status_code,400)
        self.post('/api/platform/admin/media/'+asset['id'],{'published':True})
        self.assertEqual(self.post('/api/platform/admin/lessons/'+lid,{'revision':1,'action':'publish','content':content}).status_code,200)
        item=legacy.app.test_client().get('/api/platform/lessons/'+lid).json['lesson']['blocks'][0];self.assertEqual(item['value'],asset['url']);self.assertNotIn('embed_url',item)
        with legacy.app.test_client().get(asset['url'],headers={'Range':'bytes=0-15'}) as response:self.assertEqual(response.status_code,206);self.assertEqual(len(response.data),16)
        self.post('/api/platform/admin/media/'+asset['id'],{'published':False})
        self.assertEqual(legacy.app.test_client().get(asset['url']).status_code,404)
        wrong=self.audio()['url']
        self.assertEqual(self.post('/api/platform/admin/courses/'+cid+'/lessons',{**content,'blocks':[{'type':'video','value':wrong}]}).status_code,400)

    def test_invalid_video_timeouts_and_role(self):
        self.assertEqual(self.upload(b'not a video').status_code,400)
        self.assertEqual(self.upload(b'\x00\x00\x00\x18ftypbroken').status_code,400)
        raw=synthetic_video()
        with patch('video_media.subprocess.run',side_effect=subprocess.TimeoutExpired('ffmpeg',5)):
            with self.assertRaises(ValueError):clean_video(raw)
        self.assertTrue(clean_video(synthetic_video()).startswith(b'\x00'))
        legacy.users[self.name]['role']='student';legacy._save(legacy.USERS_FILE,legacy.users)
        self.assertEqual(self.upload(synthetic_video()).status_code,403)

    def test_video_backup_restore_path(self):
        with tempfile.TemporaryDirectory(prefix='thana-video-restore-') as folder:
            archive=Path(folder)/'backup.zip';name='media/'+'a'*32+'.mp4'
            with zipfile.ZipFile(archive,'w') as z:
                for path,content in [('users.json','{}'),('progress.json','{}'),('lessons.json','[]')]:z.writestr(path,content)
                z.writestr(name,synthetic_video())
            target=Path(folder)/'restore';restore(archive,target,apply=True)
            self.assertEqual((target/name).read_bytes(),synthetic_video())

    def test_aac_video_decodes_and_strips_global_metadata(self):
        cleaned=clean_video(synthetic_video(audio=True))
        self.assertNotIn(b'fixture_private_metadata',cleaned)
        self.assertGreater(len(cleaned),100)

    def test_non_h264_mp4_rejected(self):
        with self.assertRaises(ValueError):clean_video(synthetic_video(codec='mpeg4'))
