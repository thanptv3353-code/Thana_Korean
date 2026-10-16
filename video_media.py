"""Validate and remux bounded local H.264 MP4 clips without network protocols."""
import re
import subprocess
import tempfile
import threading
from pathlib import Path
import imageio_ffmpeg

_MAX_BYTES=10*1024*1024
_GATE=threading.BoundedSemaphore(1)


def _run(args,timeout):
    try:
        return subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-nostdin','-hide_banner','-max_alloc','67108864',*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,check=False)
    except (OSError,RuntimeError,subprocess.TimeoutExpired) as exc:
        raise ValueError('Video validation unavailable or timed out') from exc


def clean_video(raw):
    if not raw or len(raw)>_MAX_BYTES or raw[4:8]!=b'ftyp':raise ValueError('Use MP4, maximum 10 MB')
    if not _GATE.acquire(blocking=False):raise BlockingIOError('Another video is being checked; retry shortly')
    try:
        with tempfile.TemporaryDirectory(prefix='thana-video-') as directory:
            source=Path(directory)/'input.mp4';target=Path(directory)/'clean.mp4';source.write_bytes(raw)
            common=['-protocol_whitelist','file,pipe','-threads','1','-i',str(source)]
            remux=_run([*common,'-map','0:v:0','-map','0:a:0?','-c','copy','-map_metadata','-1','-map_metadata:s','-1','-map_chapters','-1','-movflags','+faststart','-f','mp4',str(target)],10)
            if remux.returncode or not target.exists() or target.stat().st_size>_MAX_BYTES:raise ValueError('Invalid or oversized video')
            # Probe only the remuxed clip: uploaded metadata must not impersonate
            # codec/duration fields in FFmpeg's human-readable diagnostics.
            probe=_run(['-protocol_whitelist','file,pipe','-threads','1','-i',str(target)],5).stderr.decode('utf-8','replace')
            video=re.search(r'Video: ([^,\s]+).*?\b(\d{2,5})x(\d{2,5})\b',probe)
            audio=re.search(r'Audio: ([^,\s]+)',probe)
            duration=re.search(r'Duration: (\d+):(\d+):(\d+(?:\.\d+)?)',probe)
            if not video or video[1]!='h264' or not duration or (audio and audio[1]!='aac'):raise ValueError('Use H.264 MP4 with optional AAC audio')
            seconds=int(duration[1])*3600+int(duration[2])*60+float(duration[3])
            if not 0<seconds<=300 or int(video[2])*int(video[3])>1920*1080:raise ValueError('Maximum 5 minutes and 1920×1080 pixels')
            checked=_run(['-v','error','-xerror','-protocol_whitelist','file,pipe','-threads','1','-c:v','h264','-c:a','aac','-i',str(target),'-map','0:v:0','-map','0:a:0?','-progress','pipe:1','-f','null','-'],20)
            frames=[int(n) for n in re.findall(rb'^frame=(\d+)',checked.stdout,re.M)]
            if checked.returncode or not frames or max(frames)<1:raise ValueError('Video could not be decoded')
            return target.read_bytes()
    finally:_GATE.release()
