# friendly-calliope
Toolkit for converting Calliope inputs/outputs to friendly data.

By default, Calliope stores data as multidimensional NetCDFs, which can be handled with Calliope functionality built on xarray. To communicate this data easily with other models, this toolkit enables anybody to re-package parts of a NetCDF (or collection of them) in to the friendly_data format.

For more information on Calliope, see [here](https://github.com/calliope-project/calliope).

For more information on friendly data, see [here](https://github.com/sentinel-energy/friendly_data).

This branch is suitable for processing multiple system designs within a SPORES MGA run.

To start processing, run ``friendly-data-results.py`` in a command line. The first argument is the path to results folder, and the second argument is the path to intended directory to store the processed friendly result in ``.csv`` format. An example is the following.

```bash
python friendly-data-results.py results/ friendly-results/
```
