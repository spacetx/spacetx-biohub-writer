import csv

import click
from dataclasses import dataclass
from io import IOBase
from typing import Iterable, Mapping, Optional, Sequence, Tuple, Union

import numpy as np
from slicedimage import ImageFormat, Tile, WriterContract

from starfish.core.experiment.builder import FetchedTile, TileFetcher, write_irregular_experiment_json
from starfish.core.types import Axes, Coordinates, CoordinateValue, Number

SHAPE = {Axes.Y: 500, Axes.X: 1390}


# TODO: (ttung) this is to be removed with the next release of the starfish package, which has the fix to make
#  TileIdentifier usable as a dictionary key (https://github.com/spacetx/starfish/pull/1417).
@dataclass(eq=True, order=True, frozen=True)
class TileIdentifier:
    """Data class for encapsulating the location of a tile in a 6D tensor (fov, round, ch, zplane,
    y, and x)."""
    fov_id: int
    round_id: int
    ch_id: int
    zplane_id: int


@dataclass
class TileData:
    xc_min: Number
    xc_max: Number
    yc_min: Number
    yc_max: Number
    zc_min: Number
    zc_max: Number
    path: str
    sha256: str


class BiohubWriterContract(WriterContract):
    def tile_url_generator(self, tileset_url: str, tile: Tile, ext: str) -> str:
        return f"{tile.provider.s3_prefix}{tile.provider.tile_data.path}"

    def write_tile(
            self,
            tile_url: str,
            tile: Tile,
            tile_format: ImageFormat,
            backend_config: Optional[Mapping] = None,
    ) -> str:
        return tile.provider.tile_data.sha256


class BiohubInplaceTile(FetchedTile):
    """These tiles contain all zeroes.  This is irrelevant to the actual experiment construction
    because we are using in-place mode.  That means we build references to the tiles already on S3 and any data that is
    used is merely metadata (tile shape, tile coordinates, and tile checksum)."""
    def __init__(self, tile_data: TileData, tile_width: int, tile_height: int, s3_prefix: str):
        self.tile_data = tile_data
        self.tile_width = tile_width
        self.tile_height = tile_height
        self.s3_prefix = s3_prefix

    @property
    def shape(self) -> Mapping[Axes, int]:
        return {Axes.Y: self.tile_height, Axes.X: self.tile_width}

    @property
    def coordinates(self) -> Mapping[Union[str, Coordinates], CoordinateValue]:
        return {
            Coordinates.X: (self.tile_data.xc_min, self.tile_data.xc_max),
            Coordinates.Y: (self.tile_data.yc_min, self.tile_data.yc_max),
            Coordinates.Z: (self.tile_data.zc_min, self.tile_data.zc_max),
        }

    def tile_data(self) -> np.ndarray:
        return np.zeros(shape=(self.shape[Axes.Y], self.shape[Axes.X]), dtype=np.float32)


class BiohubInplaceFetcher(TileFetcher):
    def __init__(
            self,
            tile_data_by_tile_identifier: Mapping[TileIdentifier, TileData],
            tile_width: int,
            tile_height: int,
            s3_prefix: str,
    ):
        self.tile_data_by_tile_identifier = tile_data_by_tile_identifier
        self.tile_width = tile_width
        self.tile_height = tile_height
        self.s3_prefix = s3_prefix

    def get_tile(self, fov: int, r: int, ch: int, z: int) -> FetchedTile:
        tile_identifier = TileIdentifier(fov, r, ch, z)
        tile_data = self.tile_data_by_tile_identifier[tile_identifier]
        return BiohubInplaceTile(tile_data, self.tile_width, self.tile_height, self.s3_prefix)


def convert_str_to_Number(value_str: str) -> Number:
    """Converts a string into a Number.  Conversions to integers are preferred, and if that fails,
    we attempt to convert to a float."""
    try:
        return int(value_str)
    except ValueError:
        pass
    return float(value_str)


def parse_csv_data(csv_file: IOBase) -> Mapping[TileIdentifier, TileData]:
    csv_handle = csv.DictReader(csv_file)

    results: Mapping[TileIdentifier, TileData] = {
        TileIdentifier(
            int(row['fov']),
            int(row['round']),
            int(row['ch']),
            int(row['zplane'])):
        TileData(
            convert_str_to_Number(row['xc_min']), convert_str_to_Number(row['xc_max']),
            convert_str_to_Number(row['yc_min']), convert_str_to_Number(row['yc_max']),
            convert_str_to_Number(row['zc_min']), convert_str_to_Number(row['zc_max']),
            row['path'],
            row['sha256']
        )
        for row in csv_handle
    }
    return results


@click.command()
@click.option(
    "--csv-file",
    type=(str, click.File()),
    multiple=True,
    required=True,
    metavar="<IMAGE-TYPE CSV-FILE>",
    help="Source the tile data for <IMAGE-TYPE> from <CSV-FILE>.  This may be specified mulitple times to get all the"
         "constituent images for an experiment.",
)
@click.option(
    "--s3-prefix",
    required=True,
    help="prefix to append to every path, e.g., s3://starfish.data.spacetx/osmFISH/formatted/",
)
@click.option(
    "--tile-width",
    type=int,
    required=True,
    help="width of each tile, in px",
)
@click.option(
    "--tile-height",
    type=int,
    required=True,
    help="height of each tile, in px",
)
@click.option(
    "-o", "--output-dir",
    type=click.Path(exists=True, file_okay=False),
    required=True,
)
def main(
        csv_file: Sequence[Tuple[str, IOBase]],
        tile_width: int,
        tile_height: int,
        s3_prefix: str,
        output_dir: str
) -> None:
    tile_data_by_image_name: Mapping[str, Mapping[TileIdentifier, TileData]] = {
        name: parse_csv_data(csv_file)
        for name, csv_file in csv_file
    }

    tile_identifier_by_image_name: Mapping[str, Iterable[TileIdentifier]] = {
        name: tile_data.keys()
        for name, tile_data in tile_data_by_image_name.items()
    }

    tile_fetcher_by_image_name: Mapping[str, TileFetcher] = {
        name: BiohubInplaceFetcher(tile_data, tile_width, tile_height, s3_prefix)
        for name, tile_data in tile_data_by_image_name.items()
    }

    write_irregular_experiment_json(
        output_dir,
        ImageFormat.TIFF,
        image_tile_identifiers=tile_identifier_by_image_name,
        tile_fetchers=tile_fetcher_by_image_name,
        writer_contract=BiohubWriterContract(),
    )


if __name__ == "__main__":
    main()
