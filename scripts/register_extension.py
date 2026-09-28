#!/usr/bin/env python3
"""Enregistre l'extension Live Wallpaper & Sudo Root dans extensions.json."""

import json
import sys
import tempfile
import time
from pathlib import Path

def register():
    targets = [
        Path('/var/tmp/visual_extensions/extensions.json'),
        Path.home() / '.vscode/extensions/extensions.json',
        Path.home() / 'reseau/Perso/.vscode/extensions/extensions.json'
    ]

    base_entry = {
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
            'installedTimestamp': int(time.time() * 1000),
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
            if t.exists():
                try:
                    exts = json.loads(t.read_text(encoding='utf-8'))
                except (OSError, json.JSONDecodeError) as exc:
                    print(f"Ignoré, registre d'extensions invalide ({t}): {exc}", file=sys.stderr)
                    continue
                if not isinstance(exts, list):
                    print(f"Ignoré, format inattendu dans {t}", file=sys.stderr)
                    continue
            else:
                exts = []
            def extension_id(entry):
                if not isinstance(entry, dict):
                    return None
                identifier = entry.get('identifier')
                return identifier.get('id') if isinstance(identifier, dict) else None

            previous = next(
                (
                    e for e in exts
                    if extension_id(e) == 'budicuy.live-wallpaper'
                ),
                None
            )
            metadata = dict(base_entry['metadata'])
            if previous:
                previous_metadata = previous.get('metadata', {})
                if isinstance(previous_metadata, dict) and previous_metadata.get('installedTimestamp'):
                    metadata['installedTimestamp'] = previous_metadata['installedTimestamp']
            exts = [
                e for e in exts
                if extension_id(e) != 'budicuy.live-wallpaper'
            ]
            target_ext_path = t.parent / 'budicuy.live-wallpaper-99.0.0'
            target_ext_dir = str(target_ext_path)
            entry = dict(base_entry)
            entry['metadata'] = metadata
            entry['location'] = {
                '$mid': 1,
                'fsPath': target_ext_dir,
                'external': target_ext_path.as_uri(),
                'path': target_ext_dir,
                'scheme': 'file'
            }
            exts.append(entry)
            with tempfile.NamedTemporaryFile(
                mode='w', encoding='utf-8', dir=t.parent,
                prefix=f'.{t.name}.', suffix='.tmp', delete=False
            ) as handle:
                temp_path = Path(handle.name)
                json.dump(exts, handle, indent=2)
                handle.flush()
            temp_path.replace(t)
        except OSError as exc:
            print(f"Impossible d'enregistrer l'extension dans {t}: {exc}", file=sys.stderr)

if __name__ == '__main__':
    register()
