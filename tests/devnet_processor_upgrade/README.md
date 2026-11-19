# Devnet processor external-wSOL regression

This test uses an offline LiteSVM fixture with pinned Devnet account captures
and native CPI binaries. It exercises the corrected processor with a separate
pool-vault SOL credit and checks exact output, receipt conservation and
rollback. The older binary is used only for the historical comparison. Public
chain validation and Loader installation are separate evidence.

Build the stripped candidate using the [processor build instructions](../../programs/htfp-devnet-processor/README.md).
Use the captured Linux runtime with `solders==0.26.0`,
`jsonalias==0.1.1` and `typing_extensions==4.16.0`. The imported
`solders.abi3.so` must have SHA-256
`648e13d02ec2e8555d751e38980e01faa5cbb47c2e7d7262f3a2103caa3afa02`.
Supply the retained fixture root separately. The branch carries the test,
profile, ABI and exact input digests. The archived captures and ELF fixtures
stay outside this source branch.

```sh
python3 -B tests/devnet_processor_upgrade/test_external_wsol.py \
  --candidate target/htfp-devnet-processor/artifacts/htfp-devnet-processor.so \
  --fixture-root "$HTFP_DEVNET_FIXTURES"
```

Paths below are relative to the fixture root. The test verifies each digest
before loading its file.

| Fixture path | SHA-256 |
| --- | --- |
| `evidence/devnet_processor_upgrade/read-001/STATE.json` | `345fb91868316ef6a1bd9451c0a7ea97373adeb80344d06f528e51fdb5d7e9fa` |
| `evidence/devnet_processor_upgrade/read-001/RESULT.json` | `c11ff27bc67e9fe74b6a0a3563d23b58e10c656bde77a5ad18592b4485665353` |
| `evidence/devnet_processor_upgrade/read-003/RESULT.json` | `b0ee1224c3e98328ddd17c1c918cbf250f797a50328745a76e3d6b2b87d0cfa2` |
| `evidence/devnet_processor_upgrade/read-004/RESULT.json` | `05b5ab889220ccccc207c5b23476c5e6676ebe7c935f748fe59bedddff6b4b7e` |
| `evidence/devnet_processor_upgrade/read-001/token2022.so` | `b781b71d230a9910de4d3c103e72608f597fc73c83ee207242ac82b708382a6a` |
| `evidence/devnet_processor_upgrade/read-001/amm.so` | `30a9273dda17d7b3513889af1dab1185d9facc4756a6edf36c42f30ba228d8d1` |
| `evidence/devnet_processor_upgrade/read-001/legacy_token.so` | `8190d3f7ceb6cb7a7a8d8924bff89f9f611e15ce1f806f2b6237f3311a98f697` |
| `evidence/devnet_processor_upgrade/build-supervisor/build-001/enabled.so` | `fcb1e58e60c1d30087792626966053498bcbc01962922e93dac51c31dfd00415` |
