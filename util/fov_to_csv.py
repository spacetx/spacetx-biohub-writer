from csv import DictWriter
from io import IOBase
from pathlib import Path
from typing import MutableMapping

import click
import slicedimage
from slicedimage.backends._disk import _FileLikeContextManager
from starfish.types import Axes, Coordinates


@click.command()
@click.argument("spacetx-json", type=click.Path(exists=True, dir_okay=False))
@click.argument("csv", type=click.File("w"))
def convert_spacetx_json_to_csv(spacetx_json: str, csv: IOBase):
    spacetx_json_path = Path(spacetx_json).absolute()
    _, name, baseurl = slicedimage.io.resolve_path_or_url(spacetx_json)
    data = slicedimage.io.Reader.parse_doc(name, baseurl)
    assert isinstance(data, slicedimage.Collection)

    csvwriter = DictWriter(
        csv,
        [
            "fov",
            "round",
            "ch",
            "zplane",
            "xc_min",
            "xc_max",
            "yc_min",
            "yc_max",
            "zc_min",
            "zc_max",
            "path",
            "sha256",
        ]
    )
    csvwriter.writeheader()

    seen_fov_nums: MutableMapping[int, str] = dict()
    for name, tileset in data.all_tilesets():
        fov_num = int("".join([character for character in name if character.isdigit()]))

        if fov_num in seen_fov_nums:
            raise ValueError(f"both {name} and {seen_fov_nums[fov_num]} resolve to the same fov number")
        seen_fov_nums[fov_num] = name

        for tile in tileset.tiles():
            row = {
                'fov': str(fov_num),
                'round': str(tile.indices[Axes.ROUND]),
                'ch': str(tile.indices[Axes.CH]),
                'zplane': str(tile.indices[Axes.ZPLANE]),
                'xc_min': str(tile.coordinates[Coordinates.X][0]),
                'xc_max': str(tile.coordinates[Coordinates.X][1]),
                'yc_min': str(tile.coordinates[Coordinates.Y][0]),
                'yc_max': str(tile.coordinates[Coordinates.Y][1]),
                'zc_min': str(tile.coordinates[Coordinates.Z][0]),
                'zc_max': str(tile.coordinates[Coordinates.Z][1]),
                'sha256': tile.sha256,
            }

            # getting the path is a brittle operation
            for closure_contents in tile._numpy_array_future.__closure__:
                cell_contents = closure_contents.cell_contents

                if isinstance(cell_contents, _FileLikeContextManager):
                    path = Path(cell_contents.path).relative_to(spacetx_json_path.parent)
                    break
            else:
                raise ValueError(f"Could not find the path")
            row['path'] = path

            csvwriter.writerow(row)


if __name__ == "__main__":
    convert_spacetx_json_to_csv()
