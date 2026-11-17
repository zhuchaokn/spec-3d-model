#!/usr/bin/env python3
"""Read Bambu 3MF metadata without extracting or modifying the project."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile


def inspect(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    result = {'file': str(path.resolve()), 'bytes': path.stat().st_size,
              'sha256': digest.hexdigest(), 'limitations':
              'Metadata only; does not validate geometry, bed fit, slicing or physical prints.'}
    with zipfile.ZipFile(path) as archive:
        damaged = archive.testzip()
        if damaged:
            raise ValueError(f'ZIP integrity failed: {damaged}')
        result['zip_integrity'] = 'passed'
        names = set(archive.namelist())
        config = 'Metadata/project_settings.config'
        if config in names:
            settings = json.loads(archive.read(config))
            keys = ('printer_model', 'printer_variant', 'filament_colour',
                    'sparse_infill_density', 'sparse_infill_pattern', 'enable_prime_tower')
            result['project_settings'] = {key: settings.get(key) for key in keys}
        config = 'Metadata/model_settings.config'
        if config in names:
            root = ET.fromstring(archive.read(config))
            result['objects'] = len(root.findall('object'))
            result['plate_count'] = len(root.findall('plate'))
            result['plates'] = []
            for plate in root.findall('plate'):
                meta = {item.get('key'): item.get('value') for item in plate.findall('metadata')}
                result['plates'].append({'metadata': meta,
                                         'instances': len(plate.findall('model_instance'))})
        else:
            result['plate_count'] = None
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.file), ensure_ascii=False, indent=2))
    except (OSError, ValueError, zipfile.BadZipFile, ET.ParseError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
