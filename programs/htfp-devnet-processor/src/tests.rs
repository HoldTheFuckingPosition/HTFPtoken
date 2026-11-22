use super::*;
#[test]
fn all_builds_reject_malformed_wire() {
    for bytes in [&b""[..],&b"HTFP"[..],&b"HTFP\x02\x03"[..],&b"HTFP\x01\x07"[..]] {
        assert_eq!(process_instruction(&PROGRAM,&[],bytes),Err(fail(7000)));
    }
}
#[cfg(not(feature="devnet-metadata"))]
#[test]
fn default_profile_denies_all_valid_tags() {
    for tag in 0..=6 {
        let wire=[b'H',b'T',b'F',b'P',1,tag];
        assert_eq!(process_instruction(&PROGRAM,&[],&wire),Err(fail(7015)));
    }
}
#[cfg(all(
    feature = "devnet-metadata",
    not(any(feature = "devnet-tax-processor", feature = "production-volume-policy"))
))]
#[test]
fn metadata_core_alone_does_not_enable_processing() {
    for tag in 3..=5 {
        let wire=[b'H',b'T',b'F',b'P',1,tag];
        assert_eq!(process_instruction(&PROGRAM,&[],&wire),Err(fail(7015)));
    }
}
#[cfg(feature="devnet-tax-processor")]
#[test]
fn tax_binding_preserves_core_and_canonical_public_pdas() {
    assert_eq!(verify_profile(&PROGRAM),Ok(()));
    assert_eq!(verify_profile(&Pubkey::new_from_array([42;32])),Err(fail(7001)));
    assert_eq!(&processing_profile::PROCESSING_PREIMAGE[..],include_bytes!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../config/devnet-processor/PREIMAGE.bin")));
    assert_eq!(processing::verify_binding(),Ok(()));
    let expected_config:[u8;175]=CAPTURED_CONFIG;
    assert_eq!(config_data(1).unwrap(),expected_config.to_vec());
    assert_eq!(COMMITMENT,[194,79,162,39,151,181,177,48,72,209,122,60,33,242,6,57,144,223,153,72,35,43,193,62,252,194,248,151,54,19,3,175]);
    let(k,b)=Pubkey::find_program_address(&[b"htfp-volume",MINT.as_ref()],&PROGRAM);
    assert_eq!((k,b),(processing_profile::VOLUME,254));
    let(k,b)=Pubkey::find_program_address(&[b"htfp-settle-auth",MINT.as_ref()],&PROGRAM);
    assert_eq!((k,b),(processing_profile::SETTLE_AUTHORITY,254));
    for(sequence,expected,bump)in [(0u64,solana_program::pubkey!("9YBqCmWD5qzwULg7BdfmxQrBEB2HzcTuuZx4p36e88x2"),254),(1u64,solana_program::pubkey!("ZqZqXhdfemxNoM2hYzAMVPc8c3aZXphiTK95v5q5Tvk"),255)] {
        assert_eq!(Pubkey::find_program_address(&[b"htfp-tmp-wsol",MINT.as_ref(),&sequence.to_le_bytes()],&PROGRAM),(expected,bump));
    }
}
#[cfg(feature="devnet-tax-processor")]
const CAPTURED_CONFIG:[u8;175]=[72, 84, 70, 80, 67, 70, 71, 49, 1, 0, 1, 254, 253, 255, 255, 100, 92, 51, 40, 67, 65, 31, 53, 156, 170, 108, 202, 93, 69, 187, 198, 42, 67, 154, 59, 183, 106, 14, 57, 110, 186, 32, 134, 179, 45, 105, 207, 6, 221, 246, 225, 238, 117, 143, 222, 24, 66, 93, 188, 228, 108, 205, 218, 182, 26, 252, 77, 131, 185, 13, 39, 254, 189, 249, 40, 216, 161, 139, 252, 30, 86, 223, 225, 159, 61, 247, 238, 114, 7, 40, 26, 100, 224, 223, 129, 130, 136, 17, 204, 34, 147, 199, 237, 182, 110, 204, 122, 176, 49, 45, 106, 176, 105, 227, 29, 253, 33, 8, 177, 205, 54, 128, 41, 188, 236, 115, 132, 148, 93, 129, 133, 145, 95, 129, 137, 60, 189, 28, 87, 15, 124, 72, 62, 194, 79, 162, 39, 151, 181, 177, 48, 72, 209, 122, 60, 33, 242, 6, 57, 144, 223, 153, 72, 35, 43, 193, 62, 252, 194, 248, 151, 54, 19, 3, 175];
