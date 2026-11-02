# Compare supplied redirect observations

Experimental preview companion to Redirect Preflight, Python 3.10+ standard library.
For operators who already have authorized, first-response HTTP observations in a CSV.
This tool does not fetch URLs, follow redirects, verify capture provenance or freshness,
resolve relative Location values, normalize URLs, or diagnose indexing/canonicals.
Never treat a clean result as deployment success. Run the separate map preflight first.

Map header: `source,target`. Observations header: `source,status,location`.
Supply raw first-response status and Location, not a followed final response.
Expectations: either 301 or 308, and Location exactly equal to the mapped target.
Relative Location is legal HTTP but will mismatch an absolute target here: investigate
capture/server context manually. 302/307 may be intentional outside a permanent migration;
this experiment flags them only because it applies a permanent-redirect expectation.
Missing, duplicate/ambiguous and extra-source observations are reported by CSV record.
Duplicate or invalid map sources are rejected; duplicate observations are never selected.
Header-only inputs report zero expected rows; that provides no coverage evidence.
Files are UTF-8 (optional BOM), limited to 2 MB and 20,000 data records each.
Reports omit supplied URLs and Location values. Input files remain unchanged and may
contain sensitive data; protect them and share only reviewed reports.

Run from this directory:

```sh
python3 compare_observations.py map.csv observations.csv
python3 -m unittest -v test_redirect_preflight test_compare_observations
```

Exit 0 means supplied observations match this narrow expectation, 1 means findings,
2 means input/usage failure. A clean comparison says nothing about chains in the map,
live availability, final destinations, user agents, caching, TLS, SEO or future behavior.
Automated synthetic CLI tests ran on Linux/Python 3.12. Real HTTP captures,
Windows and macOS have not been tested. MIT licensed; no support SLA.

## Try a synthetic example

Download this repository using **Code → Download ZIP**, extract it, and save
these two files in the extracted directory. Do not use this example in production.

`map.csv`:

```csv
source,target
https://example.org/old,https://example.net/new
```

`observations.csv`:

```csv
source,status,location
https://example.org/old,307,https://example.net/new
```

Run `python3 compare_observations.py map.csv observations.csv`. It exits **1**,
reporting `unexpected_status` at map record 2 and observation record 2.
Change only `307` to `301` in the synthetic observation; the same command exits
**0** with one matched record and no findings. This edits the fixture, not a
server: it demonstrates the comparator and does not verify a deployment.
