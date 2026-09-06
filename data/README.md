# Data

Two things live here, and only one of them is committed.

| Path | Committed | What it is |
| --- | --- | --- |
| `data/raw/LSWMD.pkl` | **No** | The WM-811K distribution, downloaded locally. Check the licence on the page you download it from before redistributing. See [docs/data.md](../docs/data.md). |
| `data/subsets/*.json` | Yes | The evaluation index: which wafers the benchmark scores, their pattern labels and grid shapes, plus the filters and seed that selected them. |

Build an index from a local copy of the dataset:

```bash
python -m nano.subset --raw data/raw/LSWMD.pkl --wafers 12 --seed 0
```

The index lets anyone reconstruct the same evaluation set from their own copy of WM-811K, without
this repository redistributing the data.
