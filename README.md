# Redirect Preflight

Check an exact URL-to-URL redirect map before importing it. This free MIT-licensed
command-line preview reads a local CSV and flags duplicate sources, cycles,
redirect chain edges and invalid records. Python 3.10+; no dependencies.

## Run

Download this repository using **Code → Download ZIP**, extract it, and open a
terminal in the extracted directory:

```sh
python3 redirect_preflight.py example.csv
```

The supplied example exits 1 and reports three chain edges plus one cycle at
records 4 and 5. Exit 0 means no findings; 1 means findings; 2 means an unreadable,
malformed or oversized input. On Windows, `py -3` may replace `python3`; Windows
and macOS have not been tested. Automated CLI tests ran on Linux/Python 3.12.

Create your own UTF-8 CSV with exactly these two columns, in this order:

```csv
source,target
https://example.org/old,https://example.org/new
```

This clean example exits 0. A UTF-8 BOM is accepted. Limits: 2,000,000 input bytes,
20,000 data records, and the Python CSV parser's field-size limit. Record numbers
start at 2 after the header; quoted multiline fields still count as one record.
JSON output lists record numbers and issue types, without copying input URLs or
file paths. Input files are read only; the program makes no network requests.

## Interpret findings

- `duplicate_source`: a source appears more than once, including identical rows.
- `cycle`: these unique-source records form a closed loop, including self-loops.
- `chain_edge`: one mapping points to another unique-source mapping. Each edge is
  reported separately; cycles also contain chain edges.
- `ambiguous_target`: a mapping points to a duplicated source. Resolve duplicates
  first; they are excluded from cycle analysis rather than choosing a winner.
- `invalid_record`: wrong column count or unsupported URL. Only absolute HTTP(S)
  URLs without whitespace, credentials, fragments or backslashes are accepted.
  Query strings are accepted but are not copied to output.

Comparisons use **exact strings**. No case folding, percent-decoding, trailing
slash adjustment, IDN conversion or other normalization occurs. URLs that a
server treats as equivalent can therefore remain distinct here. This tool does
not validate every URL grammar rule, HTTP status, destination availability,
regex rules, web-server precedence, canonical tags or migration completeness.
A clean report does not establish that deployment will work. Resolve findings
and test the actual server configuration separately.

Run the included automated synthetic checks with:

```sh
python3 -m unittest -v
```

Bug reports can be filed through repository issues. Use minimal synthetic data;
do not post private URLs, credentials or customer exports. No support SLA.

For a worked correction sequence, see [Review a redirect CSV before import](REVIEW-MAP.md).
