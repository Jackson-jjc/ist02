# Experiment code

Run all commands in this directory. The complete installation, dataset layout, experiment mapping, and expected results are documented in the [repository README](../README.md) and [reproducibility guide](../REPRODUCIBILITY.md).

Quick validation:

```bash
python validate_setup.py --datasets all --include-unet
python smoke_test.py
```

Main R2 experiment:

```bash
python run_revised_experiment.py
```

The code reads dataset locations from `SCTAS_R2_ROOT`, `SCTAS_R1_ROOT`, and `SCTAS_INT_ROOT`. Runtime outputs are ignored by Git and are written to `results/` unless `SCTAS_RESULTS_ROOT` is set.
