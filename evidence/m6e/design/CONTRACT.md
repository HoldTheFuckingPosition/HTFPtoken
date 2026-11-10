# M6E four-account accounting-state inspector

This is the Stage A contract authorized by S132 and assigned by S134 after the
actual proposal Review PASS S133. Product implementation, test execution and
target calls remain gated on exact design/oracle Review and an internal coding
handoff. All quantities and identities below describe the existing synthetic
local-m3 profile. They select no production parameter or public deployment.

## Scope and trust

The single future Python 3.12 stdlib tool inspects exactly Config, Inventory,
Mint and Custody records in one explicit local file. It reports supplied byte
fields and F13/SEC04 accounting coverage. It does not contact a network or
construct instructions, transactions, signatures, wallets or services. It
does not read Reserve, Rent, Clock, Volume, external holders or discovery data.
There is no backing calculation, quote, recovery estimate, R transition,
processing eligibility or active-fee calculation.

The only selected profile is `LOCAL_M3_ACCOUNTING_V1`; omitted/null/UNCONFIGURED
fails closed. `PROFILE.json` preserves all twelve public identities and the
entire 477-byte preimage from the existing local genesis. Its SHA-256 commitment
is `8d21208a43f93594bd687987ea36d0bcff92d4940532721b61bdc9e0689f0075`.
No first-writer mint, new initializer, public account or economic value is added.
The initializer/genesis keys are public artificial test identities, not secure
deployment keys. Production is `UNCONFIGURED`.

Stage B must embody independently compiled exact PROFILE size/SHA pins and
authenticate the fixed packaged dependency on every selected local request.
Only that artifact is authenticated. The report's source hashes describe the
embodied rule versions, including on an error; they do not attest current
source files, native source-to-binary equivalence or public deployment.

Input addresses, owners, executable flags and bytes remain caller assertions.
Computing a hash, matching declared metadata, or satisfying every local
predicate cannot authenticate a bank, native account, historical association,
same-bank coherence, freshness, ownership, authorization or receipt. Arbitrary
inputs do not inherit the historical test fixtures' provenance. Fixed assurance
fields in REQUIREMENTS apply unchanged to every result, including ERROR.

## Exact request and IO

`REQUIREMENTS.json` is the exhaustive schema/catalog and prevails for field
names, messages, typed paths, source arrays, validation precedence and gates.
There is one request operation, so no operation field is accepted:

```json
{
  "schema": "htfp-accounting-state-request-v1",
  "profile": "LOCAL_M3_ACCOUNTING_V1",
  "accounts": {
    "config": {"address": "...", "owner": "...", "executable": false, "data_hex": "..."},
    "inventory": {"address": "...", "owner": "...", "executable": false, "data_hex": "..."},
    "mint": {"address": "...", "owner": "...", "executable": false, "data_hex": "..."},
    "custody": {"address": "...", "owner": "...", "executable": false, "data_hex": "..."}
  }
}
```

There are exactly four named roles and four fields in each record. All are
required; root profile alone is optional so the default is unconfigured.
Unknown fields, including caller-supplied hashes, slots, verified/provenance
labels, lamports, paths, endpoints or amounts, are rejected. No input controls
a profile pathname, current supply override or semantic rule.

Pubkeys are canonical Base58 of exactly32 bytes,32..44 characters, with exact
re-encoding; no curve or real-ownership check follows. Executable is an exact
JSON boolean. Hex is lowercase ASCII, even length0..1024 characters; empty or
wrong role length is a conformance finding, while malformed in-bound hex is a
fixed input error. Length and SHA-256 are derived from supplied bytes.

Read at most16385 bytes and reject input above16384. Use strict UTF-8/no BOM,
duplicate-key rejection including escaped equivalents, and reject all numeric
literals/nonfinite tokens. Booleans and null remain typed JSON values. Scan
all decoded keys/strings for unpaired surrogates before checking container
depth4 and decoded string length1024. Valid escaped pairs are valid Unicode
scalars but must still satisfy their field grammar. Parser RecursionError
maps to DEPTH_EXCEEDED. Global string bounds precede typed hex validation.

After parsing: reject root nonobject/unknown keys first; missing/wrong-type/
unsupported schema is INVALID_SCHEMA; missing accounts then INVALID_SHAPE at
`$`; profile selection then dependency authentication precede inner account
grammar. Require the exact accounts object before examining records. Visit
Config, Inventory, Mint, Custody; require each exact record shape before
address, owner, executable type, then hex. Finish all structural validation
before producing partial account diagnostics. The first input error yields
the complete fixed ERROR shape, never a partial result.

The CLI accepts exactly one explicit pathname and writes only stdout. Wrong
argument count or a leading `-` argument, including `--help`, gives CLI_USAGE;
`./-name` is a pathname. Empty/unreadable/OS-overlong paths are INPUT_UNREADABLE.
Request and fixed dependency IO use read-only nonblocking open, fstat the
opened descriptor as regular before reading, bounded read, and close every
opened descriptor. Symlinks resolving to regular files are permitted. No
request/environment profile path, stdin mode, output file or fallback exists.
Packaged PROFILE is7433 bytes; read at most7434. Changed, missing, truncated,
oversized or nonregular dependency data gives SOURCE_BINDING_ERROR. Standard
OSError/ValueError/TypeError IO failures use fixed errors without raw OS or
caller-text echoes. Arbitrary custom PathLike code exceptions outside those
classes are outside the public input-value contract.

Future public API is `process_bytes(bytes) -> (report, exit_code)`,
`process_file(path) -> (report, exit_code)`, and `format_report(report) -> bytes`.
Wrong Python type for process_bytes raises TypeError; process_file handles
standard os.open pathname errors as specified. Format serializes an unmodified
returned report rather than accepting arbitrary report objects for validation.
No import-time IO or shared mutable returned report references are allowed.
No old product, API, test harness or native module may be imported/executed.

## Role predicates and native encodings

For every role independently compare address, declared expected runtime owner
(H for Config/Inventory, Token-2022 for Mint/Custody), and declared executable
false. These comparisons are conformance checks on assertions. A wrong length
adds one DATA_LENGTH_MISMATCH and skips that role's binary predicates/facts;
other roles and all metadata comparisons still proceed. With exact length,
collect all applicable independent binary findings; do not stop at the first.

Config175 must equal initialized `config_data(1)` in every byte: discriminator,
LE version, initialized1, canonical four-bump vector, M/Token-2022/Reserve/H
references and genesis commitment. The nine disjoint comparisons cover all175
bytes. Flag0 is an initialization intermediate outside this initialized-state
contract, not a successful partly initialized configuration. The Reserve
reference does not supply the omitted Reserve account's data or balance.

Inventory20 has exact discriminator, version1, canonical bump and raw guard
byte. Guard0 and1 are recognized serialized local-m3 values;1 means in-flight,
not corrupt and not an operation-entry guarantee. Guard2/3 remain raw facts
but are outside this profile, as are4..255. Do not silently enable local-m4b
semantics or certify a coherent F17 frame without omitted Volume/Instructions
state. R is the LEu64 field at12:20, without an invented R<=supply condition.

Mint278 is the minimal type1 account with zero82:165 padding and exactly
TransferFeeConfig type1/length108. Validate decimals7, initialized1, parsed
supply0..10^19, issuance/freeze authorities None, extension fee-config authority
absent, withdrawal authority TaxAuthority, older schedule(7,u64MAX,0) and newer
(9,u64MAX,800). The four fee-extension relationship checks apply only when its
header exactly identifies the expected payload. Padding, type, base checks
and option groups remain independent. Positive mint withholding is valid;
do not import M6A's fixed-bank zero condition or Initialize's genesis zeros.
Stored epochs do not identify the active fee without authenticated Clock.

Custody178 is the minimal type2 account, exactly TransferFeeAmount type2/
length8, token mint M, token owner TaxAuthority, initialized/unfrozen state1,
no delegate or close authority, allowance0 and nonnative representation.
Positive spendable and withheld amounts are permitted u64 values. No holder
ImmutableOwner/MemoTransfer/CpiGuard extras are admitted to this minimal role.

Base COptionPubkey uses u32LE tag0=None, ignoring its inactive32-byte payload;
tag1=Some is outside the selected absent-authority constraints; another tag
is malformed. Some and malformed findings are mutually exclusive per field.
This applies separately to Mint issuance/freeze and Custody delegate/close.
Custody allowance must still equal zero even when delegate is None.

Custody native COption-u64 is distinct: tag109:113 zero ignores the inactive
eight bytes113:121; tag1 is native and unsupported here; other tags are
malformed. Extension nullable authorities instead use raw32 zero/nonzero
representation. There is no blanket all-zero rule over unused native payloads.

## Partial facts, accounting and reports

Every structurally valid record is shown with address, declared owner,
declared executable flag, computed data byte count/SHA and its independent
CONFORMANT/NONCONFORMANT role result. Raw account hex is not echoed. Failed
metadata, authorities or selected-profile predicates do not by themselves
erase otherwise layout-gated parsed fields. These are supplied byte facts,
not evidence of a valid native bank.

The exact field gates are:

- Raw inventory_guard requires only exact20 bytes, even with bad discriminator.
- R additionally requires Inventory discriminator/version, not bump/guard.
- Mint supply/withheld require exact278, zero mint padding, type1 and exact
  type1/length108 TLV header. Other base/authority/schedule failures preserve
  those parsed fields.
- Custody spendable/withheld require exact178, type2 and exact type2/length8
  TLV header. Other base/owner/option/state failures preserve parsed fields.

Unavailable fields are null, never fabricated zeros. This explicit partial
diagnostic policy differs from handler validation order and grants no runtime
authority. A tag's malformed authority cannot turn an offset field into a
trusted token balance.

Aggregate accounting requires all four roles to meet every selected-profile
predicate, including declared metadata. Guard1 satisfies serialization, but
its operation eligibility remains unassessed. If R<=C, assessment is COVERED,
unbooked spendable is exactly C-R and origin is always UNKNOWN. If R>C,
assessment is UNDERCOVERED with a single INVENTORY_UNDERCOVERED finding at
`accounting` and null surplus. No wrapping, clamping or withholding rescue.
Any role nonconformance makes accounting UNASSESSED and surplus null.

Keep R, Custody spendable, Custody withheld and Mint withheld distinct. Do not
sum withholding into C, label surplus proven donations/revenue, impose a new
R<=supply/global conservation rule or claim a future Recover amount. Four
records cannot reconstruct all native supply or authenticate a tax receipt.

The report has exactly the twelve root keys declared in REQUIREMENTS. Fixed
source/profile references and assurance apply also to ERROR. Normal reports
have error null and account/fact diagnostics. No findings gives CONFORMANT/0;
any finding gives NONCONFORMANT/1. Input/dependency errors give ERROR/2, profile
UNCONFIGURED, accounts null, all facts null, accounting UNASSESSED/null/UNKNOWN,
and findings empty. Complete bounded input bytes retain their SHA on errors;
usage, unreadable and oversized input have null input hash.

Findings contain only fixed code/path/message/source_ids. Deduplicate by
(path,code) and sort bytewise by that pair. Report numbers, monetary fields
and byte counts are canonical decimal strings; flags are booleans and absent
fields null. Output is exactly json.dumps with ensure_ascii=true, sorted keys,
indent2 plus LF, UTF-8; stderr empty for fixed errors. No arbitrary keys,
binary data, error details or verification claim are echoed.

## Bound and later verification

REPORT_BOUND proves at most45 simultaneous conformance findings. Its literal
maximum-count witness is documentary, not native output. The conservative
all-input envelope includes every possible catalog/path entry, including
mutually exclusive options and an impossible simultaneous error/normal report,
and maximizes every variable field. Its17217-byte size bounds all declared
reports under the fixed serialization, below the65536-byte output cap. The
certificate is a grammar argument, not sampling only the witness.

EXAMPLE/VECTORS are explicit documentary counterfactual byte banks; they do
not become genuine native history. The independent oracle will bind actual
retained M3 events823/824/827 separately, with their original source/ELF/native
associations and differences from current H source. Nothing re-executes them.

MATRIX enumerates129 C obligations and16 separately initiated G calls. The
initial128 recommendation yields to this explicit coverage; hard1024 per role
across all failed/superseded runs remains. Compatible C aliases may share an
actual case only when the frozen union proves both obligations; each G is a
separate call, including repetitions. Generated comparisons use independent
full expected reports: withholding-only changes preserve coverage; inactive
None payload changes preserve semantics; admissible equal C/R translations
preserve surplus. Input/data hashes must change correctly. No decoder-derived
expected values, PBT dependency, exhaustive or shrinking claim is introduced.

Only after design PASS/internal handoff may NEW tools/htfp_accounting_state/,
tests/m6e/ and evidence/m6e/author/ be assigned. Product has no agent quotas,
ledger, campaign role or disk policy. Verification owns prospective fsync
journals for every external invocation, exact full raw input/stdout/stderr/
exit/source/profile-copy/FIFO evidence and cumulative counts, including errors.
Use anonymous FIFO with writer closed before child, stdin readfd at
/proc/self/fd/0, fstat FIFO and descriptor closure; no persistent special files.
Isolated package copies keep every Python file byte-identical; only the
explicit copied PROFILE artifact differs or is missing/nonregular.

One serial complete author campaign precedes a distinct ROOT capture/raw audit
and final exact Review. Preserve failures/generations; do not repeat a passed
full campaign without a correction. All prior files remain frozen. Design is
limited to512KiB, later author source/tests/evidence1.5MiB, all M6E4MiB, with
2GiB free. No HTTP/native/network/build/install/key/signing/public/deployment,
production-choice or deferred M5 action occurs. Approval covers these internal
stages, but local conformance is neither implementation acceptance, public
readiness nor founder deliverable acceptance.
