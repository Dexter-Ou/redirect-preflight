# Review a redirect CSV before import

Use this checklist for an **exact URL-to-URL map**. Redirect Preflight checks a
local file without contacting its URLs. It does not generate server rules or
approve a migration. Keep the original export and work on a separate copy.

## Prepare the map

Download and extract the [source ZIP](https://codeload.github.com/Dexter-Ou/redirect-preflight/zip/59559bb87a3d31201cdf98b1e0dab7f843e307ff).
Python 3.10+ is required; no dependency installation. The CLI has been tested on
Linux/Python 3.12; Windows and macOS are untested.

Export UTF-8 CSV with exactly `source,target` as the header. Supply absolute
HTTP(S) URLs. Preserve the URL spelling your actual redirect system uses: the
checker does no normalization. Do not paste private maps into public issues.

Save this synthetic example as `review.csv` in the extracted directory:

```csv
source,target
https://example.org/old,https://example.org/intermediate
https://example.org/intermediate,https://example.org/current
https://example.org/loop-a,https://example.org/loop-b
https://example.org/loop-b,https://example.org/loop-a
```

Run:

```sh
python3 redirect_preflight.py review.csv
```

This exits **1**, with chain edges at records **2→3**, **4→5**, **5→4** and
a cycle containing records **4,5**. Records count CSV records, including the
header; a quoted multiline field is still one record. Reports omit input URLs
and paths, so keep your private CSV available to locate each finding.

## Resolve deliberately

1. Fix `invalid_record` findings and resolve every `duplicate_source`. Identical
   duplicate rows are still reported. If a row has `ambiguous_target`, its target
   is a duplicated source. The checker excludes duplicated sources from cycle
   analysis; it does not choose which rule wins.
2. Break each cycle by deciding the intended final destination. Do not guess
   from the report alone. Check the approved content plan.
3. Review chain edges. Where the migration plan calls for direct redirects,
   map each old URL directly to the intended final destination. Confirm that
   destination separately before changing the map.
4. Run the checker again after each reviewed change. It never edits your input.

For this synthetic plan, replace `review.csv` with:

```csv
source,target
https://example.org/old,https://example.org/current
https://example.org/intermediate,https://example.org/current
https://example.org/loop-a,https://example.org/current
https://example.org/loop-b,https://example.org/current
```

The same command exits **0**, with four valid records and no findings.
Converging targets are allowed; duplicate **sources** are the issue.

## Interpret the exit and finish the migration review

- **0:** no findings in this exact-string map.
- **1:** findings need review. This is the expected result for the first example.
- **2:** input could not be read or parsed, or exceeded limits. Correct the input
  problem before interpreting a report as a completed check.

A clean report does not verify destination availability, HTTP status codes,
query handling, trailing-slash/case equivalence, regex rules, rule precedence,
canonical tags, or missing URLs. Test the actual configuration separately in
an authorized staging environment, using the migration plan and rollback
procedure. Do not import this synthetic example into production.

The input limit is 2,000,000 bytes and 20,000 data records, with the Python CSV
parser's field-size limit. Only absolute HTTP(S) URLs without whitespace,
credentials, fragments or backslashes are supported. Query strings are allowed.
For a bug report, provide a minimal synthetic map, command, exit status and
expected behavior through [repository issues](https://github.com/Dexter-Ou/redirect-preflight/issues).
Do not include customer URLs, tokens or exports. MIT licensed; no support SLA.
