"""Compiled reviewed rule-version references; no current/public verification."""

PROFILE_NAME = 'LOCAL_M3_HISTORICAL_V1'

PROFILE_BYTES = 5607

PROFILE_SHA256 = 'c8afce638b45fe84bbf8154ff0fd370463ce963b9e2f2b4fef694ef040d112fd'

SOURCE_BINDINGS = {'DECISION_REGISTER.md': '9910deba190701a6bc11d91393c9d32f5b8e656027c7925fb4f13959bce1879f',
 'HTFP_FUNCTIONAL_SPEC.md': '6f80fab441729fb742cbb6fe893e7e8944a1aa79edf0750155e848e2c4540eb9',
 'OPEN_QUESTIONS.md': '3a8abdfc46b6117a268343811579c73a7dc8ec05b9e0f4e8c0a097e8cd71708a',
 'SECURITY_REQUIREMENTS.md': '966ca82678f4df1cfee21c3649c29e7df304b41b46c097cb9d76a42730804602',
 'config/m3/local_profile.json': '8c39db647774d1e24946aa8cebf00d18ee527a6af47a3c5d1c8f614b92398f6a',
 'config/m4b/abi.json': '1a6ee1ea7a003f0b48914db22a21073985d376ad38ef824ca833134333a91234',
 'evidence/M6D_AUTHORIZATION.json': 'd0feae9293ae08d0c5a9314b267c97afa01eccafea7c873a3755875f369b2e3d',
 'evidence/M6D_OFFLINE_RECOVER_PROPOSAL.md': '18b4baf244da1cf3417e03ce1ec04900b86b93a963c52edfcea8b5e3e073ea77',
 'evidence/M6D_PROPOSAL_REVIEW.json': '78d019dc348956fb27c65ba9da734e7a4b4ecaf5fdaac4fc590799d85f2132e8',
 'evidence/M6D_STAGE_A_HANDOFF.json': '8fac5339c078c3ddc2f6239702b8524ac6adcc9793bba871f3ebb25f395881bc',
 'programs/htfp/src/lib.rs': 'c4ecf74099de5175d0940f469f809f699bbbebdf69327e129e638215c16799cd',
 'programs/htfp/src/profile.rs': '0b115a8b0321979f38459a8e93351a96c7275dbb8c94099731fdef073ab6df2a'}

ASSURANCE = {'assessments': {'actual_booked_R_change': 'UNASSESSED',
                 'actual_native_harvest_withdraw_and_recovered_receipt': 'UNASSESSED',
                 'current_public_deployment_and_future_execution': 'UNASSESSED',
                 'custody_withholding_spendable_and_booked_R_coverage': 'UNASSESSED',
                 'execution_context_fee_payer_and_consent': 'UNASSESSED',
                 'frozen_source_native_compatibility': 'UNASSESSED',
                 'inventory_state_inflight_and_transaction_fee_barrier': 'UNASSESSED',
                 'packet_compute_account_loading_wallet_fit': 'UNASSESSED',
                 'protected_account_runtime_owners_executable_flags': 'UNASSESSED',
                 'source_owners_mints_state_extensions': 'UNASSESSED',
                 'source_withholding_and_absent_closed_representation': 'UNASSESSED'},
 'authorization_verified': False,
 'evidence_level': 'OFFLINE_STATIC_ONLY',
 'execution_guaranteed': False,
 'holder_signature_required_by_recover': False,
 'production_readiness': 'NOT_ASSESSED',
 'public_verification': 'NOT_PERFORMED',
 'receipt_verified': False,
 'signatures_verified': False,
 'tax_authority_outer_signature_required_by_recover': False}

ERROR_MESSAGES = {'CLI_USAGE': 'Use exactly one local request file.',
 'DEPTH_EXCEEDED': 'Input exceeds the nesting limit.',
 'INPUT_TOO_LARGE': 'Input exceeds the byte limit.',
 'INPUT_UNREADABLE': 'Input must be a readable regular file.',
 'INVALID_ACCOUNT_COUNT': 'Account count must equal six plus the body source count.',
 'INVALID_DATA_HEX': 'Expected bounded lowercase even-length hexadecimal data.',
 'INVALID_JSON': 'Input must be strict JSON without duplicate keys or numeric literals.',
 'INVALID_PUBKEY': 'Expected a canonical Base58 public key of 32 bytes.',
 'INVALID_SCHEMA': 'Unsupported request schema.',
 'INVALID_SHAPE': 'Input fields or types do not match the request schema.',
 'INVALID_TEXT': 'Input contains an invalid Unicode scalar.',
 'INVALID_UTF8': 'Input must be strict UTF-8 without BOM.',
 'INVALID_WIRE_COUNT': 'Recover source count exceeds the local ABI bound.',
 'INVALID_WIRE_HEADER': 'Expected HTFP version 1 tag 1.',
 'INVALID_WIRE_LENGTH': 'Recover body must contain exactly 8 bytes.',
 'PROFILE_UNCONFIGURED': 'Select the explicit historical local profile.',
 'SOURCE_BINDING_ERROR': 'The fixed packaged profile failed integrity validation.',
 'UNSUPPORTED_PROFILE': 'Unsupported profile.'}

FINDINGS = {'DUPLICATE_FIXED': {'message': 'Fixed account list contains a repeated key.',
                     'source_ids': ['F', 'H']},
 'DUPLICATE_SOURCE': {'message': 'Explicit source list contains a repeated key.',
                      'source_ids': ['F', 'H']},
 'FIXED_KEY_MISMATCH': {'message': 'Fixed account key differs from the historical profile.',
                        'source_ids': ['P', 'G', 'H']},
 'MISSING_PRIVILEGE': {'message': 'Descriptor privilege union does not meet the role minimum.',
                       'source_ids': ['F', 'H']},
 'PROGRAM_ID_MISMATCH': {'message': 'Program ID differs from the fixed historical profile.',
                         'source_ids': ['P', 'G', 'H']},
 'PROTECTED_SOURCE': {'message': 'Explicit source uses a fixed protected protocol key.',
                      'source_ids': ['F', 'SEC', 'H', 'P']},
 'SOURCES_TOO_MANY': {'message': 'Recover intent permits at most thirty-two explicit sources.',
                      'source_ids': ['F', 'H']}}

FIXED_ROLES = ('config', 'inventory', 'mint', 'custody', 'tax_authority', 'token2022')

