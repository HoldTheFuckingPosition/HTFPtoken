//! Bounded economic header guard; ongoing cosmetics are deliberately not decoded.
use super::{fail, key, option_key, part, u16_at, u64_at, MINT, TAX_AUTHORITY, INITIALIZER, SUPPLY, CREATION_EPOCH, ACTIVATION_EPOCH};
use solana_program::{entrypoint::ProgramResult, program_error::ProgramError};

struct Parsed<'a> { supply:u64, withheld:u64, metadata:&'a[u8] }

fn parse(data:&[u8])->Result<Parsed<'_>,ProgramError> {
    check!(data.len()>=82 && data[44]==7 && data[45]==1,7002);
    // Native None ignores its inactive pubkey payload; examine each tag in order.
    check!(option_key(data,0)?.is_none(),7016);
    check!(option_key(data,46)?.is_none(),7016);
    check!(data.len()>=166 && data[82..165].iter().all(|b|*b==0) && data[165]==1,7002);
    check!((430..=65885).contains(&data.len()),7004);
    let mut pos=166usize;
    let (mut fee,mut pointer,mut metadata)=(None,None,None);
    // Exactly three records. No index by attacker tag or traversal of cosmetics.
    for _ in 0..3 {
        check!(pos!=data.len(),7004);
        let tag=u16_at(data,pos)?;
        let len=usize::from(u16_at(data,pos+2)?);
        match tag {
            1=>check!(fee.is_none() && len==108,7004),
            18=>check!(pointer.is_none() && len==64,7004),
            19=>check!(metadata.is_none() && len>=80,7004),
            _=>return Err(fail(7004)),
        }
        pos=pos.checked_add(4).ok_or(fail(7002))?;
        let value=part(data,pos,len)?;
        match tag {1=>fee=Some(value),18=>pointer=Some(value),19=>metadata=Some(value),_=>return Err(fail(7004))}
        pos=pos.checked_add(len).ok_or(fail(7002))?;
    }
    check!(pos==data.len(),7004);
    let fee=fee.ok_or(fail(7004))?;
    let pointer=pointer.ok_or(fail(7004))?;
    let metadata=metadata.ok_or(fail(7004))?;
    let supply=u64_at(data,36)?;
    check!(supply<=SUPPLY,7016);
    check!(fee[..32].iter().all(|b|*b==0) && key(fee,32)?==TAX_AUTHORITY,7016);
    check!(u64_at(fee,72)?==CREATION_EPOCH && u64_at(fee,80)?==u64::MAX && u16_at(fee,88)?==0,7016);
    check!(u64_at(fee,90)?==ACTIVATION_EPOCH && u64_at(fee,98)?==u64::MAX && u16_at(fee,106)?==800,7016);
    let withheld=u64_at(fee,64)?;
    check!(withheld<=supply,7016);
    check!(pointer[..32].iter().all(|b|*b==0) && key(pointer,32)?==MINT,7016);
    check!(key(metadata,32)?==MINT,7016);
    Ok(Parsed{supply,withheld,metadata})
}

pub(super) fn ongoing(data:&[u8])->Result<(u64,u64),ProgramError> {
    let parsed=parse(data)?;
    Ok((parsed.supply,parsed.withheld))
}

pub(super) fn bootstrap(data:&[u8])->ProgramResult {
    let parsed=parse(data)?;
    check!(data.len()==459 && parsed.metadata.len()==109,7016);
    check!(&parsed.metadata[..32]==INITIALIZER.as_ref(),7016);
    // Embedded mint and economic fields were already checked by parse.
    check!(&parsed.metadata[64..]==b"\x19\0\0\0Hold The Fucking Position\x04\0\0\0HTFP\0\0\0\0\0\0\0\0",7016);
    Ok(())
}

#[cfg(all(test,feature="testnet-metadata"))]
mod literal_tests {
    include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../tests/testnet_profile/host_cases.rs"));
}
