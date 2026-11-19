use super::*;
// Literal observed mint bytes, not a reconstructed bootstrap or existing-key fixture.
const CAPTURED_MINT:[u8;459]=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 232, 137, 4, 35, 199, 138, 7, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 108, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 151, 159, 95, 220, 242, 155, 247, 35, 20, 119, 11, 58, 249, 207, 16, 219, 232, 140, 182, 78, 54, 73, 171, 204, 56, 109, 110, 142, 165, 72, 247, 210, 0, 0, 0, 0, 0, 0, 0, 0, 184, 4, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 255, 255, 255, 255, 0, 0, 186, 4, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 255, 255, 255, 255, 32, 3, 18, 0, 64, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 100, 92, 51, 40, 67, 65, 31, 53, 156, 170, 108, 202, 93, 69, 187, 198, 42, 67, 154, 59, 183, 106, 14, 57, 110, 186, 32, 134, 179, 45, 105, 207, 19, 0, 109, 0, 52, 21, 183, 233, 223, 171, 124, 108, 165, 8, 40, 73, 42, 119, 76, 0, 154, 1, 219, 15, 117, 222, 66, 193, 132, 190, 246, 143, 108, 90, 143, 67, 100, 92, 51, 40, 67, 65, 31, 53, 156, 170, 108, 202, 93, 69, 187, 198, 42, 67, 154, 59, 183, 106, 14, 57, 110, 186, 32, 134, 179, 45, 105, 207, 25, 0, 0, 0, 72, 111, 108, 100, 32, 84, 104, 101, 32, 70, 117, 99, 107, 105, 110, 103, 32, 80, 111, 115, 105, 116, 105, 111, 110, 4, 0, 0, 0, 72, 84, 70, 80, 0, 0, 0, 0, 0, 0, 0, 0];
#[test]
fn rich_metadata_economic_header_and_cosmetic_mutability() {
    let original=CAPTURED_MINT.to_vec();
    assert_eq!(ongoing(&original),Ok((SUPPLY,0)));assert_eq!(bootstrap(&original),Ok(()));
    let mut changed=original.clone();changed[350..382].fill(0x42);changed[414..].fill(0xff);
    assert_eq!(ongoing(&changed),Ok((SUPPLY,0)));assert_eq!(bootstrap(&changed),Err(fail(7016)));
    let mut grown=original.clone();grown[348..350].copy_from_slice(&1133u16.to_le_bytes());grown.extend_from_slice(&[0x5a;1024]);
    assert_eq!(ongoing(&grown),Ok((SUPPLY,0)));assert_eq!(bootstrap(&grown),Err(fail(7016)));
    let mut inactive=original.clone();inactive[4..36].fill(0xff);inactive[50..82].fill(0xfe);
    assert_eq!(ongoing(&inactive),Ok((SUPPLY,0)));assert_eq!(bootstrap(&inactive),Ok(()));
    for offset in [0usize,46,170,202,242,250,258,260,268,276,282,314,382] {
        let mut bad=original.clone();bad[offset]^=1;
        assert_eq!(ongoing(&bad),Err(fail(7016)),"economic offset{offset}");
    }
    let mut supply=original.clone();supply[36..44].copy_from_slice(&u64::MAX.to_le_bytes());assert_eq!(ongoing(&supply),Err(fail(7016)));
    let mut wrong_tag=original.clone();wrong_tag[166..168].copy_from_slice(&2u16.to_le_bytes());assert_eq!(ongoing(&wrong_tag),Err(fail(7004)));
    let mut wrong_mint=original.clone();wrong_mint[382..414].fill(0);assert_eq!(ongoing(&wrong_mint),Err(fail(7016)));
}
