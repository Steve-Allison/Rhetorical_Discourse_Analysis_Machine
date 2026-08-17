"""Download open DISRPT / GUM discourse segmentation datasets for model training."""

import urllib.error
import urllib.request
from pathlib import Path

# Official DISRPT 2023 / 2021 segmentation dataset repositories on GitHub
DISRPT_BASE_URL = "https://raw.githubusercontent.com/disrpt/sharedtask2023/main/data"

DATASETS: dict[str, list[str]] = {
    "eng.rst.gum": [
        "eng.rst.gum_train.tok",
        "eng.rst.gum_dev.tok",
        "eng.rst.gum_test.tok",
        "eng.rst.gum_train.conll",
        "eng.rst.gum_dev.conll",
        "eng.rst.gum_test.conll",
    ],
    "eng.rst.rstdt": [
        "eng.rst.rstdt_train.tok",
        "eng.rst.rstdt_dev.tok",
        "eng.rst.rstdt_test.tok",
        "eng.rst.rstdt_train.conll",
        "eng.rst.rstdt_dev.conll",
        "eng.rst.rstdt_test.conll",
    ],
    "eng.pdtb.pdtb": [
        "eng.pdtb.pdtb_train.tok",
        "eng.pdtb.pdtb_dev.tok",
        "eng.pdtb.pdtb_test.tok",
    ],
}


def download_dataset(
    target_dir: Path | str = "data/disrpt",
    tracks: list[str] | None = None,
) -> dict[str, list[Path]]:
    """Download DISRPT segmentation dataset files to target directory."""
    dest_root = Path(target_dir)
    dest_root.mkdir(parents=True, exist_ok=True)

    selected_tracks = tracks or list(DATASETS.keys())
    downloaded_files: dict[str, list[Path]] = {}

    for track in selected_tracks:
        if track not in DATASETS:
            print(f"Unknown track: {track}. Skipping.")
            continue

        track_dir = dest_root / track
        track_dir.mkdir(parents=True, exist_ok=True)
        downloaded_files[track] = []

        for filename in DATASETS[track]:
            file_url = f"{DISRPT_BASE_URL}/{track}/{filename}"
            file_dest = track_dir / filename

            if file_dest.exists() and file_dest.stat().st_size > 0:
                print(f"File already exists: {file_dest}")
                downloaded_files[track].append(file_dest)
                continue

            print(f"Downloading {file_url} -> {file_dest}...")
            try:
                urllib.request.urlretrieve(file_url, file_dest)
                downloaded_files[track].append(file_dest)
                print(f"Successfully downloaded {filename} ({file_dest.stat().st_size} bytes)")
            except (urllib.error.URLError, OSError, ValueError) as e:
                print(f"Failed to download {filename} from {file_url}: {e}")

    return downloaded_files


if __name__ == "__main__":
    download_dataset()
