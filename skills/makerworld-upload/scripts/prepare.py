#!/usr/bin/env python3
"""Create a reviewable upload manifest and preserve original media locally."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from inspect_3mf import inspect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--file', type=Path, required=True)
    parser.add_argument('--photo', type=Path, action='append', default=[])
    parser.add_argument('--title', required=True)
    parser.add_argument('--description-file', type=Path, required=True)
    parser.add_argument('--category', required=True)
    parser.add_argument('--tag', action='append', default=[])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--draft-url')
    args = parser.parse_args()
    if len(args.title) > 50:
        parser.error('Title exceeds the observed 50-character field limit')
    if len(args.tag) > 50:
        parser.error('Too many tags')
    report = inspect(args.file)
    description = args.description_file.read_text().strip()
    if not description:
        parser.error('Description is empty')
    args.output.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output / 'publication.json'
    if manifest_path.exists():
        parser.error('Manifest already exists; resume it rather than overwriting progress')
    photos, hashes = [], {str(args.file.resolve()): report['sha256']}
    seen = set()
    for number, photo in enumerate(args.photo, 1):
        digest = hashlib.sha256(photo.read_bytes()).hexdigest()
        if digest in seen:
            parser.error('Duplicate photo contents do not represent additional real views')
        seen.add(digest)
        target = args.output / f'photo-{number:02d}{photo.suffix.lower()}'
        shutil.copyfile(photo, target)
        photos.append(str(target.resolve()))
        hashes[str(target.resolve())] = digest
    site = 'https://makerworld.com' if args.draft_url and args.draft_url.startswith('https://makerworld.com/') else 'https://makerworld.com.cn'
    manifest = {'mode': 'draft', 'site': site, 'draft_url': args.draft_url,
                'files_sha256': hashes, 'model': {'file': str(args.file.resolve()),
                'title': args.title, 'description': description, 'category': args.category,
                'tags': args.tag, 'photos': photos, 'cover': photos[0] if photos else None},
                'uploaded_media': [], 'cover_uploaded': False,
                'preflight': report,
                'publication_pending': ['Verify complete-print photo coverage and source rights before publishing']}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(json.dumps({'manifest': str(manifest_path.resolve()), 'plates': report.get('plate_count'),
                      'photo_count': len(photos), 'mode': 'draft'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
