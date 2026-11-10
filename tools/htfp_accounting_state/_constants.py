"""Embodied reviewed rule references; no current-file or public verification."""

PROFILE_NAME = 'LOCAL_M3_ACCOUNTING_V1'

PROFILE_BYTES = 7433

PROFILE_SHA256 = 'bcf092cc1980cac41679370f5ae6cec3bbda567631368d19bfeb9e1e8267dc27'

SOURCE_BINDINGS = {'ABI': '1a6ee1ea7a003f0b48914db22a21073985d376ad38ef824ca833134333a91234',
 'D': '9910deba190701a6bc11d91393c9d32f5b8e656027c7925fb4f13959bce1879f',
 'F': '6f80fab441729fb742cbb6fe893e7e8944a1aa79edf0750155e848e2c4540eb9',
 'G': '8c39db647774d1e24946aa8cebf00d18ee527a6af47a3c5d1c8f614b92398f6a',
 'H': 'c4ecf74099de5175d0940f469f809f699bbbebdf69327e129e638215c16799cd',
 'O': '3a8abdfc46b6117a268343811579c73a7dc8ec05b9e0f4e8c0a097e8cd71708a',
 'P': '0b115a8b0321979f38459a8e93351a96c7275dbb8c94099731fdef073ab6df2a',
 'PROPOSAL': 'd53231b40539fe410c4b5e8427ccf28748c5cb237054474982722cd7a60b13b8',
 'S132': '4dd7deee9b74d651b78424706c471fbaebc7ca482cc6c219c4a53c8f059de637',
 'S133': 'dce583546483699c94ee050d54b15e4e74795611a6f2975dff2a9fc7d02f1be5',
 'S134': '09aebbacf5359634d60c370efa6106b47b897dd19cc4b319b4bb7e5ed423fc8e',
 'SEC': '966ca82678f4df1cfee21c3649c29e7df304b41b46c097cb9d76a42730804602'}

ASSURANCE = {'assessments': {'active_transfer_fee': 'UNASSESSED',
                 'actual_account_ownership_and_executable_flags': 'UNASSESSED',
                 'actual_native_account_existence_and_state': 'UNASSESSED',
                 'actual_recovered_receipt_or_R_transition': 'UNASSESSED',
                 'custody_surplus_origin': 'UNASSESSED',
                 'global_supply_conservation': 'UNASSESSED',
                 'historical_or_current_bank_provenance': 'UNASSESSED',
                 'native_source_binary_and_public_runtime_equivalence': 'UNASSESSED',
                 'operation_eligibility_and_guard_frame': 'UNASSESSED',
                 'reserve_backing_and_redemption': 'UNASSESSED'},
 'authorization_verified': False,
 'declared_ownership_verified': False,
 'evidence_level': 'OFFLINE_SUPPLIED_RECORDS_ONLY',
 'execution_guaranteed': False,
 'freshness_verified': False,
 'production_readiness': 'NOT_ASSESSED',
 'provenance_verified': False,
 'public_verification': 'NOT_PERFORMED',
 'receipt_verified': False,
 'same_bank_verified': False,
 'signatures_verified': False}

ERROR_MESSAGES = {'CLI_USAGE': 'Use exactly one local request file.',
 'DEPTH_EXCEEDED': 'Input exceeds the nesting limit.',
 'INPUT_TOO_LARGE': 'Input exceeds the byte limit.',
 'INPUT_UNREADABLE': 'Input must be a readable regular file.',
 'INVALID_DATA_HEX': 'Expected bounded lowercase even-length hexadecimal account data.',
 'INVALID_JSON': 'Input must be strict JSON without duplicate keys or numeric literals.',
 'INVALID_PUBKEY': 'Expected a canonical Base58 public key of 32 bytes.',
 'INVALID_SCHEMA': 'Unsupported request schema.',
 'INVALID_SHAPE': 'Input fields or types do not match the request schema.',
 'INVALID_TEXT': 'Input contains an invalid Unicode scalar.',
 'INVALID_UTF8': 'Input must be strict UTF-8 without BOM.',
 'PROFILE_UNCONFIGURED': 'Select the explicit historical local accounting profile.',
 'SOURCE_BINDING_ERROR': 'The fixed packaged profile failed integrity validation.',
 'UNSUPPORTED_PROFILE': 'Unsupported profile.'}

FINDINGS = {'ADDRESS_MISMATCH': {'message': 'Account address differs from the fixed role identity.',
                      'source_ids': ['P', 'G', 'H']},
 'CONFIG_BUMPS_MISMATCH': {'message': 'Config canonical bump vector differs.',
                           'source_ids': ['H', 'P', 'G']},
 'CONFIG_COMMITMENT_MISMATCH': {'message': 'Config genesis commitment differs.',
                                'source_ids': ['H', 'P', 'G']},
 'CONFIG_DERIVER_MISMATCH': {'message': 'Config deriving-program binding differs.',
                             'source_ids': ['H', 'P', 'G']},
 'CONFIG_HEADER_MISMATCH': {'message': 'Config discriminator differs.',
                            'source_ids': ['H', 'P', 'G']},
 'CONFIG_INITIALIZED_REQUIRED': {'message': 'Config must contain initialized flag one.',
                                 'source_ids': ['H', 'P', 'G']},
 'CONFIG_MINT_MISMATCH': {'message': 'Config mint binding differs.', 'source_ids': ['H', 'P', 'G']},
 'CONFIG_RESERVE_MISMATCH': {'message': 'Config reserve reference differs.',
                             'source_ids': ['H', 'P', 'G']},
 'CONFIG_TOKEN2022_MISMATCH': {'message': 'Config Token-2022 binding differs.',
                               'source_ids': ['H', 'P', 'G']},
 'CONFIG_VERSION_MISMATCH': {'message': 'Config layout version differs.',
                             'source_ids': ['H', 'P', 'G']},
 'CUSTODY_ACCOUNT_TYPE_MISMATCH': {'message': 'Custody extension account type must be two.',
                                   'source_ids': ['H', 'P', 'G']},
 'CUSTODY_ALLOWANCE_NONZERO': {'message': 'Custody delegated allowance must equal zero.',
                               'source_ids': ['H', 'P', 'G']},
 'CUSTODY_CLOSE_AUTHORITY_PRESENT': {'message': 'Custody close authority must be absent.',
                                     'source_ids': ['H', 'P', 'G']},
 'CUSTODY_CLOSE_OPTION_INVALID': {'message': 'Custody close-authority COption tag must be zero or '
                                             'one.',
                                  'source_ids': ['H', 'P', 'G']},
 'CUSTODY_DELEGATE_OPTION_INVALID': {'message': 'Custody delegate COption tag must be zero or one.',
                                     'source_ids': ['H', 'P', 'G']},
 'CUSTODY_DELEGATE_PRESENT': {'message': 'Custody delegate must be absent.',
                              'source_ids': ['H', 'P', 'G']},
 'CUSTODY_MINT_MISMATCH': {'message': 'Custody token mint differs.', 'source_ids': ['H', 'P', 'G']},
 'CUSTODY_NATIVE_OPTION_INVALID': {'message': 'Custody native COption-u64 tag must be zero or one.',
                                   'source_ids': ['H', 'P', 'G']},
 'CUSTODY_NATIVE_UNSUPPORTED': {'message': 'Custody must be a nonnative token account.',
                                'source_ids': ['H', 'P', 'G']},
 'CUSTODY_STATE_MISMATCH': {'message': 'Custody token state must equal initialized and unfrozen '
                                       'one.',
                            'source_ids': ['H', 'P', 'G']},
 'CUSTODY_TLV_MISMATCH': {'message': 'Custody requires exactly TransferFeeAmount type two with '
                                     'length eight.',
                          'source_ids': ['H', 'P', 'G']},
 'CUSTODY_TOKEN_OWNER_MISMATCH': {'message': 'Custody token owner differs from TaxAuthority.',
                                  'source_ids': ['H', 'P', 'G']},
 'DATA_LENGTH_MISMATCH': {'message': 'Account data length differs from the exact role layout.',
                          'source_ids': ['H', 'F']},
 'EXECUTABLE_ACCOUNT': {'message': 'Declared account must be nonexecutable.', 'source_ids': ['H']},
 'INVENTORY_BUMP_MISMATCH': {'message': 'Inventory canonical bump differs.',
                             'source_ids': ['H', 'P', 'G']},
 'INVENTORY_GUARD_UNSUPPORTED': {'message': 'Raw guard is outside the selected local-m3 serialized '
                                            'values zero and one.',
                                 'source_ids': ['H', 'P', 'G']},
 'INVENTORY_HEADER_MISMATCH': {'message': 'Inventory discriminator differs.',
                               'source_ids': ['H', 'P', 'G']},
 'INVENTORY_UNDERCOVERED': {'message': 'Booked R exceeds Custody spendable; withheld balances do '
                                       'not cover the deficit.',
                            'source_ids': ['F', 'SEC', 'H']},
 'INVENTORY_VERSION_MISMATCH': {'message': 'Inventory layout version differs.',
                                'source_ids': ['H', 'P', 'G']},
 'MINT_ACCOUNT_TYPE_MISMATCH': {'message': 'Mint extension account type must be one.',
                                'source_ids': ['H', 'P', 'G']},
 'MINT_DECIMALS_MISMATCH': {'message': 'Mint decimals must equal seven.',
                            'source_ids': ['H', 'P', 'G']},
 'MINT_FEE_AUTHORITY_PRESENT': {'message': 'Transfer-fee configuration authority must be absent.',
                                'source_ids': ['H', 'P', 'G']},
 'MINT_FREEZE_AUTHORITY_OPTION_INVALID': {'message': 'Freeze authority COption tag must be zero or '
                                                     'one.',
                                          'source_ids': ['H', 'P', 'G']},
 'MINT_FREEZE_AUTHORITY_PRESENT': {'message': 'Mint freeze authority must be absent.',
                                   'source_ids': ['H', 'P', 'G']},
 'MINT_INITIALIZED_REQUIRED': {'message': 'Mint initialized byte must equal one.',
                               'source_ids': ['H', 'P', 'G']},
 'MINT_MINT_AUTHORITY_OPTION_INVALID': {'message': 'Mint authority COption tag must be zero or '
                                                   'one.',
                                        'source_ids': ['H', 'P', 'G']},
 'MINT_MINT_AUTHORITY_PRESENT': {'message': 'Mint issuance authority must be absent.',
                                 'source_ids': ['H', 'P', 'G']},
 'MINT_NEWER_SCHEDULE_MISMATCH': {'message': 'Stored newer transfer-fee schedule differs from the '
                                             'fixed local profile.',
                                  'source_ids': ['H', 'P', 'G']},
 'MINT_OLDER_SCHEDULE_MISMATCH': {'message': 'Stored older transfer-fee schedule differs from the '
                                             'fixed local profile.',
                                  'source_ids': ['H', 'P', 'G']},
 'MINT_PADDING_MISMATCH': {'message': 'Mint base padding must be zero.',
                           'source_ids': ['H', 'P', 'G']},
 'MINT_SUPPLY_EXCEEDS_CAP': {'message': 'Parsed mint supply exceeds the fixed initial issuance '
                                        'cap.',
                             'source_ids': ['H', 'P', 'G']},
 'MINT_TLV_MISMATCH': {'message': 'Mint requires exactly TransferFeeConfig type one with length '
                                  '108.',
                       'source_ids': ['H', 'P', 'G']},
 'MINT_WITHDRAW_AUTHORITY_MISMATCH': {'message': 'Withheld withdrawal authority differs from '
                                                 'TaxAuthority.',
                                      'source_ids': ['H', 'P', 'G']},
 'OWNER_MISMATCH': {'message': 'Declared account owner differs from the selected profile.',
                    'source_ids': ['H', 'F']}}

ROLES = ('config', 'inventory', 'mint', 'custody')

LENGTHS = {'config': 175, 'custody': 178, 'inventory': 20, 'mint': 278}

FACT_KEYS = ('supply_base_units',
 'inventory_guard',
 'booked_inventory_base_units',
 'custody_spendable_base_units',
 'custody_withheld_base_units',
 'mint_withheld_base_units')

