"""Pack or unpack the ported runs' trajectories.

The ported app records the whole case file before and after every tool call, so one sample's trajectory.json and
trajectory.jsonl hold 0.1 to 220 MB each, 4.4 GB over 100 samples. Consecutive snapshots are nearly identical, so xz
packs each file to well under 1 MB, and the repository keeps only the .xz copies.

    python phase2-env/trajectories.py unpack runs   # trajectory.json and trajectory.jsonl beside each .xz
    python phase2-env/trajectories.py pack runs     # the .xz copies, checked against the originals

Neither command overwrites a file that already exists. Standard library only; `xz -dk` unpacks the same files.
"""
import lzma
from pathlib import Path
import sys

NAMES = ('trajectory.json', 'trajectory.jsonl')


def pack(root: Path) -> None:
    done = 0
    for name in NAMES:
        for path in sorted(root.glob(f'*/ported/sample-*/{name}')):
            packed = path.with_name(path.name + '.xz')
            if packed.exists():
                continue
            data = path.read_bytes()
            compressed = lzma.compress(data)
            if lzma.decompress(compressed) != data:
                raise SystemExit(f'{path}: the packed copy does not unpack to the original.')
            packed.write_bytes(compressed)
            done += 1
    print(f'packed {done} trajectory files')


def unpack(root: Path) -> None:
    done = 0
    for packed in sorted(root.glob('*/ported/sample-*/trajectory.json*.xz')):
        path = packed.with_suffix('')
        if path.name in NAMES and not path.exists():
            path.write_bytes(lzma.decompress(packed.read_bytes()))
            done += 1
    print(f'unpacked {done} trajectory files')


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[1] not in ('pack', 'unpack'):
        raise SystemExit(__doc__)
    root = Path(sys.argv[2])
    pack(root) if sys.argv[1] == 'pack' else unpack(root)


if __name__ == '__main__':
    main()
