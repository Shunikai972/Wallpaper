#!/usr/bin/env python3
"""Enregistre l'extension Live Wallpaper & Sudo Root dans extensions.json."""

import json
from pathlib import Path

def register():
    targets = [
        Path('/var/tmp/visual_extensions/extensions.json'),
        Path.home() / '.vscode/extensions/extensions.json',
        Path.home() / 'reseau/Perso/.vscode/extensions/extensions.json'
    ]

    lw_entry = {
        'identifier': {'id': 'budicuy.live-wallpaper'},
        'version': '99.0.0',
        'location': {
            '$mid': 1,
            'fsPath': '/var/tmp/visual_extensions/budicuy.live-wallpaper-99.0.0',
            'external': 'file:///var/tmp/visual_extensions/budicuy.live-wallpaper-99.0.0',
            'path': '/var/tmp/visual_extensions/budicuy.live-wallpaper-99.0.0',
            'scheme': 'file'
        },
        'relativeLocation': 'budicuy.live-wallpaper-99.0.0',
        'metadata': {
            'installedTimestamp': 1788946167367,
            'pinned': True,
            'source': 'custom',
            'publisherDisplayName': 'budicuy',
            'targetPlatform': 'undefined',
            'updated': False,
            'isPreReleaseVersion': False
        }
    }

    for t in targets:
        try:
            t.parent.mkdir(parents=True, exist_ok=True)
            exts = []
            if t.exists():
                try:
                    exts = json.loads(t.read_text(encoding='utf-8'))
                except Exception:
                    exts = []
            exts = [e for e in exts if e.get('identifier', {}).get('id') != 'budicuy.live-wallpaper']
            target_ext_dir = str(t.parent / 'budicuy.live-wallpaper-99.0.0')
            entry = dict(lw_entry)
            entry['location'] = {
                '$mid': 1,
                'fsPath': target_ext_dir,
                'external': f'file://{target_ext_dir}',
                'path': target_ext_dir,
                'scheme': 'file'
            }
            exts.append(entry)
            t.write_text(json.dumps(exts, indent=2), encoding='utf-8')
        except Exception:
            pass

if __name__ == '__main__':
    register()
