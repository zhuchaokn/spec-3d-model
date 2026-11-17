#!/usr/bin/env python3
"""Repeatable browser-frame -> MP4 export. No Blender or live-site dependency."""
import argparse, json, math, os, shutil, subprocess, sys
from pathlib import Path
P=Path(__file__).resolve().parent

def existing(candidates):
    return next((str(p) for p in candidates if p and Path(p).exists()), None)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=P.parent/'output/video/china-map-story.mp4')
    parser.add_argument('--width',type=int,default=1080)
    parser.add_argument('--height',type=int,default=1920)
    parser.add_argument('--fps',type=int,default=30)
    parser.add_argument('--start',type=float,default=0,help='Narration timeline start, seconds')
    parser.add_argument('--duration',type=float,help='Optional short preview length')
    parser.add_argument('--overwrite',action='store_true')
    parser.add_argument('--node')
    parser.add_argument('--playwright',help='Playwright package directory')
    parser.add_argument('--chromium',help='Chromium executable; default uses Playwright installation')
    args=parser.parse_args()
    if args.width<=0 or args.height<=0 or args.width%2 or args.height%2 or args.width*16!=args.height*9:
        parser.error('Use positive even 9:16 dimensions, e.g. 1080 x 1920')
    if not 1<=args.fps<=60 or not math.isfinite(args.start) or args.start<0 or (args.duration is not None and (not math.isfinite(args.duration) or args.duration<=0)):
        parser.error('Invalid frame rate or timeline interval')
    for executable in ['ffmpeg','ffprobe']:
        if not shutil.which(executable):parser.error(f'{executable} is missing; install FFmpeg first')
    bundle=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node'
    node=args.node or shutil.which('node') or existing([bundle/'bin/node'])
    if not node:parser.error('Node.js is missing')
    package=args.playwright or os.environ.get('CINEMA_PLAYWRIGHT') or existing([
        P/'node_modules/playwright',P.parents[2]/'node_modules/playwright',bundle/'node_modules/playwright'])
    chromium=args.chromium or os.environ.get('CINEMA_CHROMIUM')
    # The desktop runtime may include only Playwright's headless-shell download.
    if not chromium:
        cache=Path.home()/('Library/Caches/ms-playwright' if sys.platform=='darwin' else '.cache/ms-playwright')
        candidates=sorted(cache.glob('chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell'),key=lambda p:p.stat().st_mtime)
        chromium=existing(candidates[-1:])
    config={'root':str(P),'output':str(args.output.expanduser().resolve()),'width':args.width,'height':args.height,
            'fps':args.fps,'start':args.start,'duration':args.duration,'overwrite':args.overwrite,
            'playwright':package or 'playwright','chromium':chromium,'ffmpeg':shutil.which('ffmpeg'),'ffprobe':shutil.which('ffprobe')}
    result=subprocess.run([node,str(P/'export_video_worker.cjs')],input=json.dumps(config),text=True)
    return result.returncode

if __name__=='__main__':sys.exit(main())
