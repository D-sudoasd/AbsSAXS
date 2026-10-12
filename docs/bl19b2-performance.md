# BL19B2 batch performance and recovery evidence

Measured on 12 October 2026. The beamline inputs, full processing controls and
large derived packages remain private. Only aggregate engineering evidence is
included here. Numerical agreement does not resolve the experiment's existing
partial uncertainty budget.

## Revisions and workload

- Baseline: `722d6069df84d8e3a49771fad21702af27cceb7a`.
- Implementation: `c374339ff8f624f58d464ec06f32b6f37917480c`.
- One complete measured BL19B2 selection: 19 Pilatus 2M frames, 1679 by 1475
  pixels. The original include manifest and thickness derivation were reused.
- The same references, geometry, mask, monitor convention, thickness,
  uncertainty inputs, 1000-point K calibration, float32 intensity and float64
  uncertainty datasets were used for both revisions. Downstream integration
  retained CSR, 5500 points, `q_A^-1`, and the signed correction policy.
- Outputs included HDF5, EDF, JSON, every PNG, QC, configuration, provenance,
  manifests, individual 1D curves, directory matrix and mean/sample-standard-
  deviation tables, checksums and completion records.
- Windows 11, Python 3.12.10, Ryzen 9 9950X3D (16 cores/32 logical CPUs), about
  61.4 GiB RAM. Raw input was on an external USB disk; new outputs were on a
  SATA HDD. NumPy 2.1.2, pyFAI 2026.5.0, h5py 3.16.0, FabIO 2026.6.0,
  tifffile 2026.7.14, Matplotlib 3.11.1, Pillow 12.3.0.

## Complete delivery timing

Each observation launched a fresh Python process. Timing began before launch
and ended after process exit, including imports, both workflow APIs, required
writes, full 2D validation, and independent integration checksum/completion
verification. A resumed 2D frame reused the validation already performed by the
workflow instead of running that validator a second time.

The serial order was baseline, candidate, candidate, baseline; each fresh run
was followed by a full resume in its own output package. There were two
observations per revision and scenario. No process/thread count, scientific
parameter, frame count or output scope was changed between revisions.

| Scenario | Baseline seconds | Candidate seconds | Ratio | Wait reduction |
|---|---:|---:|---:|---:|
| Fresh complete delivery, mean | 54.43 | 47.44 | 1.15x | 12.8% |
| Fresh range | 51.33–57.52 | 43.71–51.18 | — | — |
| Full verified resume, mean | 17.38 | 13.38 | 1.30x | 23.0% |
| Resume range | 16.75–18.00 | 12.38–14.38 | — | — |

These are application first runs with new outputs, not guaranteed cold disk
cache runs. The shared workstation had other scientific work; its OS page cache
was not flushed and background load was not isolated. The complete ranges are
retained instead of treating the faster exploratory result as a stable speedup.
There is no statistical significance claim from two observations per variant.

| Fresh-run resource, mean | Baseline | Candidate |
|---|---:|---:|
| Process CPU, user + system | 89.63 s | 79.17 s |
| Peak resident memory | 1506.19 MiB | 1103.86 MiB |
| Peak private memory | 1429.69 MiB | 1060.42 MiB |
| Logical process reads | 2735.70 MiB | 2754.94 MiB |
| Logical process writes | 563.39 MiB | 560.55 MiB |

Resources were sampled every 50 ms for the direct child. CPU and memory values
can miss a final sampling interval. Process I/O counters include cached/logical
I/O and are not physical disk traffic. Reads did not decrease: the candidate
also verifies PNG structure and content checksums. Resume peak RSS changed from
567.33 to 578.70 MiB; the fresh-run memory reduction does not apply to every mode.

## Bottlenecks and implemented changes

1. **2D generation/publication** was the largest phase: baseline mean 36.36 s.
   HDF5 compression dominated the original 19-frame diagnostic. Automatic
   chunks produced 5376 stored chunks per frame across intensity and ten
   uncertainty datasets. Lossless gzip level 1 with 128 by 256 chunks reduces
   this to 924; smaller images use capped chunk dimensions. A representative
   frame's measured full HDF5 write changed from 1.31 to 0.96 s. A separate
   layout trial measured 0.98 to 0.68 s; neither local number is the end-to-end
   speedup. The compared complete candidate package was approximately 0.5%
   smaller, so this improvement did not trade large storage growth for speed.
2. **Required output validation** averaged 12.82 s before and 8.39 s after the
   change. The same checksums, schemas, units, shapes, dtypes, finite-value
   checks, masks and uncertainty contracts remain active. The new HDF5 layout
   improves sequential reads as well as writes.
3. **Uncertainty construction** retained eight squared detector arrays and
   repeatedly stacked them for reductions, then copied ten masked components.
   It now accumulates variances in component order with explicit per-pixel
   unknown tracking and retains the overflow gate for known contributions.
   Only newly owned budget arrays are masked in place. A representative frame
   changed from 0.53 to 0.32 s for this step; full fresh-run RSS fell about 27%.
4. **QC/preview work** repeatedly partitioned the same finite intensities for
   percentiles. QC now obtains all three quantiles in one call and gives the
   already calculated preview limits to the renderer. Full figure rendering
   remains a material cost. Source snapshot hashes and independent I/O-boundary
   verification remain because they provide input stability and integrity
   evidence; they were not replaced with a persistent cache.

Downstream 1D processing averaged about 2.66 s before and 2.45 s after. The
existing single integrator per package was retained. Extra workers were not
introduced without a campaign-level throughput measurement.

## Result agreement and recovery

The final complete packages were compared independently:

- 209 HDF5 scientific arrays, 517,593,725 scalar values: identical shapes,
  dtypes, units and raw value bits, including NaN placement; maximum error 0.
- All 19 EDF files/headers/payloads, 19 PNG files/pixels, 19 individual 1D CSVs,
  directory matrix, and mean/sample-standard-deviation CSVs were identical.
- Every candidate PNG checksum matched its file and full Pillow decoding
  passed. Both integration packages' 46 checksum entries and all references
  were valid. Scientific metadata and canonical selection/frame signatures
  matched their recorded inputs.
- Allowed differences were package paths, recorded runtime/code provenance,
  HDF5 lossless container bytes and their digests, verified preview digests,
  resume records, and derived signatures/checksum indexes. No unexpected
  differences or missing outputs were found. The candidate also has a
  persistent one-byte lock file.

Both revisions were deliberately terminated after five committed frames while
the sixth HDF5 was being written. The baseline then refused the incomplete
existing set. The candidate's journal retained or rebuilt only its interrupted
private stage, reused the first five frames, processed the remaining fourteen,
and delivered all nineteen frames and the full 1D package. This is a recovery
capability result; no speed ratio is assigned to a baseline that did not finish.
The candidate took 60.31 s including interruption and immediate resumption;
the resumed child took 44.97 s. All 209 scientific arrays matched a complete
fresh run bit for bit, 59 EDF/PNG/profile/statistical files matched by bytes,
the first fifteen committed HDF5/EDF/PNG files remained unchanged, and no
private stages or incomplete markers remained.

Package locks use operating-system locks, so a terminated writer does not leave
a permanently held lock. Completed frame sidecars are published last, after all
required members are staged. An interrupted/partial 2D run retains an incomplete
marker and cannot enter downstream integration. Existing unknown fragments
without a workflow journal still fail closed. 1D recovery removes only its known
private temporary writes and retains content/signature checks on final files.

Legacy PNGs without a checksum are rebuilt once from already verified pixels
before gaining a reusable content binding. Missing or corrupt PNGs are repaired.
Preview checksum changes are excluded from the scientific 1D metadata digest;
all detector/scientific fields remain bound, so display repair does not force
recalculation of an already valid 1D curve. This one-time legacy migration cost
was not included in the current-format resume figures above.

## Reproduction and limits

Create separate checkouts of the two revisions and a JSON object containing
the original `BL19B2Abs2DConfig` fields, excluding `output_root`. Keep private
control files and raw inputs outside Git. The benchmark never deletes inputs
or outputs and refuses an existing output root in fresh mode.
The measurement tool requires psutil, supplied by the development extra;
install the relevant BL19B2 optional dependencies as described in
[contributing](../CONTRIBUTING.md).

```powershell
py -3.12 scripts/benchmark_bl19b2.py `
  --source-root <baseline-or-candidate-checkout> `
  --config-json <private-processing-controls.json> `
  --output-root <new-independent-package> `
  --evidence-dir <separate-evidence-directory> `
  --scenario fresh
# Repeat with the same configuration/output root and --scenario resume.
```

Reports contain parent wall time, per-stage times, child resource counters,
exact package/dependency versions, inherited thread settings, configuration
digests, Git/archive identity, and hashes of every package Python source file.
Optional `--profile` is diagnostic and is not comparable to ordinary timing.

Final local validation: 1280 tests passed; full configured Ruff scope passed;
wheel/sdist build, Twine validation and actual installed-wheel CLI/import checks
passed. Unit tests cover numeric unknownness/overflow, interrupted frame commits,
preview recovery, partial completion guards, 1D temporary recovery, and real
cross-process lock contention/termination.

The entire historical campaign, GUI performance, physical cold-cache runs,
multi-package throughput tuning, all OS/Python combinations, and real 1D-only
hard termination were not measured here. HDF5 compression/readback and PNG
rendering remain the next measured targets. Expanding claims to the historical
campaign requires a comparable complete campaign measurement; the nineteen-
frame result is not such a measurement.
