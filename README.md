# spacetx-biohub-writer
Conversion tool from biohub's DB format to spacetx format

# Required columns in the CSV

| Column | Description                                                                              |
|--------|------------------------------------------------------------------------------------------|
| fov    | Field of View identifier.  Should be an integer.                                         |
| round  | Round label.  Should be an integer.                                                      |
| ch     | Channel label.  Should be an integer.                                                    |
| zplane | Zplane label.  Should be an integer.                                                     |
| xc_min | Minimum physical x-coordinate for the tile                                               |
| xc_max | Maximum physical x-coordinate for the tile                                               |
| yc_min | Minimum physical y-coordinate for the tile                                               |
| yc_max | Maximum physical y-coordinate for the tile                                               |
| zc_min | Minimum physical z-coordinate for the tile                                               |
| zc_max | Maximum physical z-coordinate for the tile                                               |
| path   | Relative path to the tile, as specified from the s3_prefix argument                      |
| sha256 | SHA256 checksum of the tile                                                              |

# Example

## Converting from a single CSV representing an image in an experiment.

```
% spacetx_biohub_writer --csv-file primary primary.csv --s3-prefix  s3://starfish.data.spacetx/osmFISH/formatted/20190626/ --tile-width 2048 --tile-height 2048 -o output
```

## Converting from multiple CSVs representing an image in an experiment.

```
% spacetx_biohub_writer --csv-file primary primary.csv --csv-file nuclei nuclei.csv --s3-prefix  s3://starfish.data.spacetx/osmFISH/formatted/20190626/ --tile-width 2048 --tile-height 2048 -o output
```
