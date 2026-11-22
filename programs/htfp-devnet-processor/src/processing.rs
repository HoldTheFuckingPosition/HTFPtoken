//! Shared tax settlement with separately bound sale policies.
use super::*;
use crate::processing_profile as p;
use solana_program::{clock::Clock,instruction::get_stack_height,sysvar::instructions::{load_current_index_checked,load_instruction_at_checked}};
fn sub(a:u64,b:u64)->Res<u64>{a.checked_sub(b).ok_or(fail(7010))}
fn put(d:&mut[u8],off:usize,n:u64){d[off..off+8].copy_from_slice(&n.to_le_bytes());}
#[cfg(not(feature = "production-volume-policy"))]
fn i64_at(d:&[u8],off:usize)->Res<i64>{Ok(i64::from_le_bytes(part(d,off,8)?.try_into().map_err(|_|fail(7019))?))}
fn u128_at(d:&[u8],off:usize)->Res<u128>{Ok(u128::from_le_bytes(part(d,off,16)?.try_into().map_err(|_|fail(7025))?))}
pub fn verify_binding()->ProgramResult{verify_binding_data(&p::PROCESSING_PREIMAGE)}
fn verify_binding_data(b:&[u8])->ProgramResult{
 check!(b.len()==1282&&hash(b).to_bytes()==p::PROCESSING_COMMITMENT,7018);
 #[cfg(not(feature = "production-volume-policy"))]
 check!(&b[..16]==b"HTFP_TAX_DEV_V01"&&u16_at(b,16)?==1&&b[18..50]==COMMITMENT&&u16_at(b,50)?==25,7018);
 #[cfg(feature = "production-volume-policy")]
 check!(&b[..16]==b"HTFP_TAX_PRD_V02"&&u16_at(b,16)?==2&&b[18..50]==COMMITMENT&&u16_at(b,50)?==25,7018);
 for(i,k)in p::ORDERED_KEYS.iter().enumerate(){check!(part(b,52+i*32,32)?==k.as_ref(),7018);}
 check!(p::PROGRAM==PROGRAM&&p::MINT==MINT&&p::CONFIG==CONFIG&&p::INVENTORY==INVENTORY&&p::TOKEN2022==TOKEN2022&&p::RESERVE==RESERVE&&p::TAX_AUTHORITY==TAX_AUTHORITY&&p::CUSTODY==CUSTODY&&p::GENESIS_OWNER==GENESIS_OWNER&&p::INITIALIZER==INITIALIZER&&p::GENESIS_HOLDING==GENESIS_HOLDING&&p::SYSTEM==SYSTEM&&p::LEGACY_TOKEN==LEGACY,7018);
 #[cfg(not(feature = "production-volume-policy"))]
 {
 check!(part(b,852,32)?==[48, 169, 39, 61, 218, 23, 215, 179, 81, 56, 137, 175, 29, 171, 17, 133, 217, 250, 204, 71, 86, 166, 237, 243, 108, 66, 243, 11, 162, 40, 216, 209],7018);
 check!(part(b,884,4)?==[240, 244, 26, 0],7018);
 check!(part(b,888,8)?==[9, 163, 38, 31, 0, 0, 0, 0],7018);
 check!(part(b,896,32)?==[183, 129, 183, 29, 35, 10, 153, 16, 222, 77, 60, 16, 62, 114, 96, 143, 89, 127, 199, 60, 131, 238, 32, 114, 66, 172, 130, 183, 8, 56, 42, 106],7018);
 check!(part(b,928,4)?==[96, 217, 10, 0],7018);
 check!(part(b,932,8)?==[9, 163, 38, 31, 0, 0, 0, 0],7018);
 check!(part(b,940,32)?==[129, 144, 211, 247, 206, 182, 203, 122, 122, 141, 137, 36, 191, 248, 159, 159, 97, 30, 21, 206, 31, 128, 111, 43, 98, 55, 243, 49, 26, 152, 246, 151],7018);
 check!(part(b,972,4)?==[56, 168, 1, 0],7018);
 check!(part(b,976,8)?==[9, 163, 38, 31, 0, 0, 0, 0],7018);
 check!(part(b,984,32)?==[229, 231, 174, 209, 26, 211, 150, 158, 234, 42, 167, 108, 139, 77, 46, 115, 234, 37, 190, 126, 107, 92, 206, 152, 155, 119, 16, 207, 84, 82, 73, 110],7018);
 check!(part(b,1016,32)?==[100, 142, 19, 208, 46, 194, 232, 85, 93, 117, 30, 56, 152, 14, 1, 250, 165, 203, 180, 124, 46, 125, 114, 98, 243, 162, 16, 60, 170, 58, 250, 2],7018);
 check!(part(b,1048,32)?==[59, 92, 162, 243, 24, 114, 97, 204, 4, 142, 35, 83, 120, 146, 66, 6, 124, 58, 255, 25, 202, 182, 113, 104, 248, 109, 187, 210, 157, 153, 242, 28],7018);
 check!(part(b,1080,8)?==[1, 0, 0, 0, 0, 0, 0, 0],7018);
 check!(part(b,1088,8)?==[232, 3, 0, 0, 0, 0, 0, 0],7018);
 check!(part(b,1096,8)?==[0, 128, 198, 164, 126, 141, 3, 0],7018);
 check!(part(b,1104,8)?==[0, 32, 61, 136, 121, 45, 0, 0],7018);
 check!(part(b,1112,8)?==[3, 0, 0, 0, 0, 0, 0, 0],7018);
 check!(part(b,1120,8)?==[192, 127, 250, 106, 0, 0, 0, 0],7018);
 check!(part(b,1128,8)?==[0, 0, 222, 201, 116, 127, 146, 48],7018);
 check!(part(b,1136,8)?==[0, 88, 133, 12, 2, 0, 0, 0],7018);
 check!(part(b,1144,8)?==[196, 9, 0, 0, 0, 0, 0, 0],7018);
 check!(part(b,1152,8)?==[196, 9, 0, 0, 0, 0, 0, 0],7018);
 check!(part(b,1160,8)?==[192, 212, 1, 0, 0, 0, 0, 0],7018);
 check!(part(b,1168,8)?==[64, 156, 0, 0, 0, 0, 0, 0],7018);
 check!(part(b,1176,2)?==[1, 0],7018);
 check!(part(b,1178,2)?==[175, 0],7018);
 check!(part(b,1180,2)?==[20, 0],7018);
 check!(part(b,1182,2)?==[89, 0],7018);
 check!(part(b,1184,2)?==[203, 1],7018);
 check!(part(b,1186,2)?==[178, 0],7018);
 check!(part(b,1188,2)?==[125, 2],7018);
 check!(part(b,1190,2)?==[236, 0],7018);
 check!(part(b,1192,2)?==[235, 15],7018);
 check!(part(b,1194,4)?==[1, 3, 4, 5],7018);
 check!(part(b,1198,2)?==[1, 2],7018);
 check!(part(b,1200,32)?==[215, 106, 0, 166, 38, 158, 202, 226, 16, 232, 61, 133, 237, 161, 91, 31, 38, 51, 205, 81, 85, 192, 243, 232, 225, 126, 221, 212, 0, 182, 108, 151],7018);
 check!(part(b,1232,32)?==[134, 113, 175, 201, 137, 193, 33, 5, 63, 155, 223, 64, 152, 58, 136, 133, 147, 155, 27, 167, 74, 165, 77, 245, 142, 251, 174, 128, 130, 7, 94, 235],7018);
 check!(part(b,1264,2)?==[32, 3],7018);
 check!(part(b,1266,8)?==[186, 4, 0, 0, 0, 0, 0, 0],7018);
 check!(part(b,1274,8)?==[255, 255, 255, 255, 255, 255, 255, 255],7018);
 check!(u64_at(b,1080)?==p::ALPHA_NUM&&u64_at(b,1088)?==p::ALPHA_DEN&&u64_at(b,1096)?==p::C_BASE&&u64_at(b,1104)?==p::REFILL_N&&u64_at(b,1112)?==p::SCALE_D&&i64_at(b,1120)?==p::START_TIMESTAMP,7018);
 check!(p::C_BASE.checked_mul(p::SCALE_D)==Some(p::CAPACITY_SCALED)&&p::INITIAL_CREDIT_SCALED==p::CAPACITY_SCALED,7018);
 check!(u64_at(b,1144)?==p::TRADE_PPM&&u64_at(b,1152)?==p::CREATOR_PPM&&u64_at(b,1160)?==p::PROTOCOL_PPM&&u64_at(b,1168)?==p::FUND_PPM,7018);
 check!(u16_at(b,1264)?==p::ACTIVE_BPS as u16&&u64_at(b,1266)?==p::ACTIVE_EPOCH&&p::ACTIVE_EPOCH==ACTIVATION_EPOCH&&p::ACTIVE_BPS==800&&p::ALPHA_DEN>0&&p::SCALE_D>0,7018);
 }
 #[cfg(feature = "production-volume-policy")]
 {
     // The preimage hash binds the exact local CPI tuple, provenance pins and
     // account layouts. Also compare the fields that the handler applies.
     check!(b[1048..1080] == p::CONFIG_HASH, 7018);
     check!(u64_at(b, 1080)? == 1 && u64_at(b, 1088)? == PRODUCTION_RESERVE_DIVISOR, 7018);
     check!(b[1096..1128].iter().all(|&byte| byte == 0), 7018);
     check!(u64_at(b, 1128)? == SUPPLY / 100 * 35 && u64_at(b, 1136)? > 0, 7018);
     check!(p::TRADE_PPM == 2500 && p::CREATOR_PPM == 500
         && p::PROTOCOL_PPM == 120_000 && p::FUND_PPM == 40_000, 7018);
     for (offset, rate) in [(1144, p::TRADE_PPM), (1152, p::CREATOR_PPM),
         (1160, p::PROTOCOL_PPM), (1168, p::FUND_PPM)]
     {
         check!(u64_at(b, offset)? == rate, 7018);
     }
     check!(p::ACTIVE_BPS == 800 && u16_at(b, 1264)? == p::ACTIVE_BPS as u16
         && u64_at(b, 1266)? == p::ACTIVE_EPOCH && p::ACTIVE_EPOCH == ACTIVATION_EPOCH
         && u64_at(b, 1274)? == u64::MAX, 7018);
 }
 Ok(())
}
fn canonical(seed:&[u8],expected:&Pubkey)->Res<u8>{let(k,b)=Pubkey::find_program_address(&[seed,MINT.as_ref()],&PROGRAM);check!(k==*expected,7018);Ok(b)}
fn bookkeeping(cfg:&AccountInfo,inv:&AccountInfo)->Res<(u64,u8)>{
 identity(cfg,&CONFIG)?;identity(inv,&INVENTORY)?;required(inv,true,false)?;check!(cfg.owner==&PROGRAM&&inv.owner==&PROGRAM&&!cfg.executable&&!inv.executable,7001);
 check!(&**cfg.try_borrow_data()?==config_data(1)?.as_slice(),7002);let d=inv.try_borrow_data()?;
 check!(d.len()==20&&&d[..8]==b"HTFPINV1"&&u16_at(&d,8)?==1&&d[10]==bumps()?[1]&&d[11]<=3,7002);Ok((u64_at(&d,12)?,d[11]))
}
#[cfg(not(feature = "production-volume-policy"))]
const VOLUME_HEADER: (&[u8; 8], u16) = (b"HTFPVOL1", 1);
#[cfg(feature = "production-volume-policy")]
const VOLUME_HEADER: (&[u8; 8], u16) = (b"HTFPVOL2", 2);

#[derive(Clone)]
struct Volume {
    #[cfg(not(feature = "production-volume-policy"))]
    credit: u64,
    #[cfg(not(feature = "production-volume-policy"))]
    last: i64,
    seq: u64,
    active: u8,
    origin: u16,
    cleanup: u16,
    nonce: u64,
}
fn volume(a:&AccountInfo)->Res<Volume>{
 identity(a,&p::VOLUME)?;required(a,true,false)?;check!(a.owner==&PROGRAM&&!a.executable&&a.data_len()==89,7019);let d=a.try_borrow_data()?;
 check!(&d[..8] == VOLUME_HEADER.0 && u16_at(&d, 8)? == VOLUME_HEADER.1
     && d[10] == canonical(b"htfp-volume", &p::VOLUME)?, 7019);
 check!(d[11..43] == p::PROCESSING_COMMITMENT, 7018);
 let v = Volume {
     #[cfg(not(feature = "production-volume-policy"))]
     credit: u64_at(&d, 43)?,
     #[cfg(not(feature = "production-volume-policy"))]
     last: i64_at(&d, 51)?,
     seq: u64_at(&d, 59)?,
     active: d[67],
     origin: u16_at(&d, 68)?,
     cleanup: u16_at(&d, 70)?,
     nonce: u64_at(&d, 72)?,
 };
 #[cfg(not(feature = "production-volume-policy"))]
 check!(v.credit <= p::CAPACITY_SCALED, 7019);
 #[cfg(feature = "production-volume-policy")]
 check!(d[43..59].iter().all(|&byte| byte == 0), 7019);
 check!(v.active <= 1 && d[80..].iter().all(|&byte| byte == 0), 7019);
 Ok(v)
}
fn write_volume(a:&AccountInfo,v:&Volume)->ProgramResult{
 let mut d=a.try_borrow_mut_data()?;check!(d.len()==89&&a.owner==&PROGRAM,7019);d.fill(0);d[..8].copy_from_slice(VOLUME_HEADER.0);d[8..10].copy_from_slice(&VOLUME_HEADER.1.to_le_bytes());d[10]=canonical(b"htfp-volume",&p::VOLUME)?;d[11..43].copy_from_slice(&p::PROCESSING_COMMITMENT);
 #[cfg(not(feature = "production-volume-policy"))]
 {
     put(&mut d, 43, v.credit);
     d[51..59].copy_from_slice(&v.last.to_le_bytes());
 }
 put(&mut d,59,v.seq);d[67]=v.active;d[68..70].copy_from_slice(&v.origin.to_le_bytes());d[70..72].copy_from_slice(&v.cleanup.to_le_bytes());put(&mut d,72,v.nonce);Ok(())
}
fn idle(v:&Volume)->ProgramResult{check!(v.active==0&&v.origin==0&&v.cleanup==0&&v.nonce==0,7021);Ok(())}
fn active(v:&Volume,current:u16,last:u16,nonce:u64)->ProgramResult{check!(v.active==1&&v.origin<=current&&v.origin<last&&v.cleanup==last&&v.nonce==nonce&&nonce>0&&nonce<=v.seq,7021);Ok(())}
fn tail(a:&AccountInfo,finishing:bool)->Res<(u16,u16,u64)>{
 identity(a,&p::INSTRUCTIONS_SYSVAR)?;check!(a.owner==&sysvar::ID&&!a.executable&&!a.is_writable&&a.data_len()>=4,7022);
 let count={let d=a.try_borrow_data()?;u16_at(&d,0)?};let current=load_current_index_checked(a)?;check!(count>0&&current<count,7022);let last=count-1;
 if finishing{check!(current==last&&get_stack_height()==1,7022);}else{check!(count>=2&&current<last,7021);}
 let ix=load_instruction_at_checked(last as usize,a)?;check!(ix.program_id==PROGRAM&&ix.data.len()==14&&&ix.data[..6]==b"HTFP\x01\x05"&&ix.accounts.len()==4,7022);
 for(i,k)in [CONFIG,INVENTORY,p::VOLUME,p::INSTRUCTIONS_SYSVAR].iter().enumerate(){let m=&ix.accounts[i];check!(m.pubkey==*k,7022);if i==1||i==2{check!(m.is_writable,7022);}if i==3{check!(!m.is_writable,7022);}}
 Ok((current,last,u64_at(&ix.data,6)?))
}
pub fn initialize_processing(a:&[AccountInfo])->ProgramResult{
 check!(a.len()==5,7000);unique(a)?;let[cfg,inv,vol,payer,sys]=a else{return Err(fail(7000));};let(r,g)=bookkeeping(cfg,inv)?;check!(g&1==0,7012);check!(g==0,7021);identity(vol,&p::VOLUME)?;program(sys,&SYSTEM)?;required(payer,true,true)?;required(vol,true,false)?;check!(system_zero(payer),7001);check!(system_zero(vol),7017);
 inventory_write(inv,r,1)?;bootstrap(vol,payer,sys,89,&PROGRAM,b"htfp-volume",canonical(b"htfp-volume",&p::VOLUME)?)?;
 let v = Volume {
     #[cfg(not(feature = "production-volume-policy"))]
     credit: p::INITIAL_CREDIT_SCALED,
     #[cfg(not(feature = "production-volume-policy"))]
     last: p::START_TIMESTAMP,
     seq: 0, active: 0, origin: 0, cleanup: 0, nonce: 0,
 };
 write_volume(vol,&v)?;inventory_write(inv,r,0)?;
 let mut e=Vec::with_capacity(120);e.extend_from_slice(MINT.as_ref());e.extend_from_slice(p::VOLUME.as_ref());e.extend_from_slice(&p::PROCESSING_COMMITMENT);
 #[cfg(not(feature = "production-volume-policy"))]
 {
     e.extend_from_slice(&v.credit.to_le_bytes());
     e.extend_from_slice(&v.last.to_le_bytes());
 }
 #[cfg(feature = "production-volume-policy")]
 e.extend_from_slice(&[0; 16]); // Reserved legacy quota positions.
 e.extend_from_slice(&v.seq.to_le_bytes());event(4,&e);Ok(())
}
pub fn finalize(a:&[AccountInfo],data:&[u8])->ProgramResult{
 check!(data.len()==14&&a.len()==4,7000);unique(a)?;let[cfg,inv,vol,iv]=a else{return Err(fail(7000));};let(r,g)=bookkeeping(cfg,inv)?;let mut v=volume(vol)?;check!(g&1==0,7012);let(cur,last,nonce)=tail(iv,true)?;check!(nonce==u64_at(data,6)?,7022);
 if g==0{idle(&v)?;check!(nonce==v.seq.checked_add(1).ok_or(fail(7026))?,7022);return Ok(());}
 active(&v,cur,last,nonce)?;v.active=0;v.origin=0;v.cleanup=0;v.nonce=0;write_volume(vol,&v)?;inventory_write(inv,r,0)?;
 let mut e=Vec::with_capacity(80);e.extend_from_slice(MINT.as_ref());e.extend_from_slice(p::VOLUME.as_ref());e.extend_from_slice(&nonce.to_le_bytes());e.extend_from_slice(&v.seq.to_le_bytes());event(5,&e);Ok(())
}
struct NativeWsol {
    amount: u64,
    native_reserve: u64,
    surplus_lamports: u64,
}

fn native_wsol(a: &AccountInfo, owner: &Pubkey) -> Res<NativeWsol> {
 check!(a.owner==&LEGACY&&!a.executable&&a.data_len()==165,7023);let d=a.try_borrow_data()?;
 check!(key(&d,0)?==p::WSOL_MINT&&key(&d,32)?==*owner&&d[108]==1&&option_key(&d,72)?.is_none()&&option_key(&d,129)?.is_none()&&u64_at(&d,121)?==0&&u32_at(&d,109)?==1,7023);
    let native_reserve = u64_at(&d, 113)?;
    let amount = u64_at(&d, 64)?;
    let backed_lamports = checked_add(amount, native_reserve)?;
    let surplus_lamports = a.lamports().checked_sub(backed_lamports).ok_or(fail(7023))?;
    Ok(NativeWsol { amount, native_reserve, surplus_lamports })
}

fn temporary_wsol_amount(a: &AccountInfo, owner: &Pubkey, rent: u64) -> Res<u64> {
    let balance = native_wsol(a, owner)?;
    check!(balance.native_reserve == rent && balance.surplus_lamports == 0, 7023);
    Ok(balance.amount)
}
fn split(q:u64,r:u64)->Res<(u64,u64)>{
 check!(q>0&&q%8==0&&q<=r,7006);Ok(((q/8)*3,(q/8)*5))
}
#[cfg(not(feature = "production-volume-policy"))]
fn volume_admission(f:u64,x:u64,credit:u64,last:i64,now:i64)->Res<(i64,u64,u64)>{
 check!(credit<=p::CAPACITY_SCALED,7019);
 check!(u128::from(f)<=u128::from(x).checked_mul(u128::from(p::ALPHA_NUM)).ok_or(fail(7010))?/u128::from(p::ALPHA_DEN),7020);
 let time=now.max(last);let elapsed=(i128::from(time)-i128::from(last))as u128;
 let available=(u128::from(credit)+elapsed.checked_mul(u128::from(p::REFILL_N)).ok_or(fail(7010))?).min(u128::from(p::CAPACITY_SCALED))as u64;
 let used=u128::from(f).checked_mul(u128::from(p::SCALE_D)).ok_or(fail(7010))?;check!(used<=u128::from(available),7020);
 Ok((time,available,sub(available,used as u64)?))
}
#[cfg(feature = "production-volume-policy")]
const PRODUCTION_RESERVE_DIVISOR: u64 = 100;

#[cfg(feature = "production-volume-policy")]
fn production_sale_admission(gross_sale: u64, effective_htfp: u64) -> ProgramResult {
    check!(gross_sale <= effective_htfp / PRODUCTION_RESERVE_DIVISOR, 7020);
    Ok(())
}

fn ceil(n:u128,d:u128)->Res<u64>{u64::try_from(n.checked_add(d-1).ok_or(fail(7010))?/d).map_err(|_|fail(7010))}
fn quote(f:u64,x:u64,y:u64,epoch:u64)->Res<(u64,u64,u64,u64,u64)>{
 let tax=if epoch>=p::ACTIVE_EPOCH{ceil(u128::from(f).checked_mul(u128::from(p::ACTIVE_BPS)).ok_or(fail(7010))?,10000)?}else{0};let input=sub(f,tax)?;
 let combined=ceil(u128::from(input).checked_mul(u128::from(p::TRADE_PPM+p::CREATOR_PPM)).ok_or(fail(7010))?,1000000)?;
 let creator=u64::try_from(u128::from(combined).checked_mul(u128::from(p::CREATOR_PPM)).ok_or(fail(7010))?/u128::from(p::TRADE_PPM+p::CREATOR_PPM)).map_err(|_|fail(7010))?;
 let trade=sub(combined,creator)?;let curve=sub(input,combined)?;
 let numerator=u128::from(curve).checked_mul(u128::from(y)).ok_or(fail(7010))?;
 let denominator=u128::from(x).checked_add(u128::from(curve)).ok_or(fail(7010))?;
 let output=u64::try_from(numerator/denominator).map_err(|_|fail(7010))?;
 let protocol=u64::try_from(u128::from(trade).checked_mul(u128::from(p::PROTOCOL_PPM)).ok_or(fail(7010))?/1000000).map_err(|_|fail(7010))?;
 let fund=u64::try_from(u128::from(trade).checked_mul(u128::from(p::FUND_PPM)).ok_or(fail(7010))?/1000000).map_err(|_|fail(7010))?;
 Ok((tax,output,protocol,fund,creator))
}
fn effective(d:&[u8],amount:u64,side:usize)->Res<u64>{let fees=u128::from(u64_at(d,341+8*side)?)+u128::from(u64_at(d,357+8*side)?)+u128::from(u64_at(d,397+8*side)?);check!(fees<u128::from(amount),7025);Ok((u128::from(amount)-fees)as u64)}
fn pool_validate(pool:&AccountInfo,cfg:&AccountInfo,obs:&AccountInfo)->Res<Vec<u8>>{
 check!(pool.owner==&p::AMM&&!pool.executable&&pool.data_len()==637&&cfg.owner==&p::AMM&&!cfg.executable&&cfg.data_len()==236&&obs.owner==&p::AMM&&!obs.executable&&obs.data_len()==4075,7025);
 check!(hash(&cfg.try_borrow_data()?).to_bytes()==p::CONFIG_HASH,7025);let d=pool.try_borrow_data()?;
 check!(d[..8]==p::POOL_DISCRIMINATOR,7025);for(off,k)in [(8,p::AMM_CONFIG),(40,GENESIS_OWNER),(72,p::VAULT_WSOL),(104,p::VAULT_HTFP),(136,p::LP_MINT),(168,p::WSOL_MINT),(200,MINT),(232,LEGACY),(264,TOKEN2022),(296,p::OBSERVATION)]{check!(key(&d,off)?==k,7025);}
 let(auth,bump)=Pubkey::find_program_address(&[b"vault_and_lp_mint_auth_seed"],&p::AMM);check!(auth==p::AMM_AUTHORITY&&d[328]==bump&&d[330..333]==[9,9,7]&&d[389]==0&&d[390]==1,7025);
 let od=obs.try_borrow_data()?;check!(od[..8]==p::OBS_DISCRIMINATOR&&od[8]<=1&&u16_at(&od,9)?<100&&key(&od,11)?==p::POOL,7025);Ok(d.to_vec())
}
fn observation_expected(mut d:Vec<u8>,now:u64,wsol:u64,htfp:u64)->Res<Vec<u8>>{
 let idx=u16_at(&d,9)? as usize;let off=43+idx*40;
 if d[8]==0{d[8]=1;put(&mut d,off,now);d[off+8..off+40].fill(0);put(&mut d,4043,now);return Ok(d);}
 let timestamp=u64_at(&d,off)?;let mut updated=u64_at(&d,4043)?;if updated==0{updated=timestamp;put(&mut d,4043,updated);}
 let elapsed=now.saturating_sub(timestamp);let dt=now.saturating_sub(updated);if elapsed==0||dt==0{return Ok(d);}
 let price0=u128::from(htfp)*(1u128<<32)/u128::from(wsol);let price1=u128::from(wsol)*(1u128<<32)/u128::from(htfp);
 let c0=u128_at(&d,off+8)?.wrapping_add(price0.checked_mul(u128::from(dt)).ok_or(fail(7010))?);let c1=u128_at(&d,off+24)?.wrapping_add(price1.checked_mul(u128::from(dt)).ok_or(fail(7010))?);
 let target=if elapsed<15{off}else{let n=(idx+1)%100;d[9..11].copy_from_slice(&(n as u16).to_le_bytes());let target=43+n*40;put(&mut d,target,now);target};d[target+8..target+24].copy_from_slice(&c0.to_le_bytes());d[target+24..target+40].copy_from_slice(&c1.to_le_bytes());put(&mut d,4043,now);Ok(d)
}
pub fn process(a:&[AccountInfo],data:&[u8])->ProgramResult{
 check!(data.len()==14&&a.len()==22,7000);unique(a)?;
 let[cfg,inv,vol,m,cust,tax,res,temp,settle,payer,t,legacy,wsol,sys,iv,amm,ac,auth,pool,hvault,wvault,obs]=a else{return Err(fail(7000));};
 identity(m,&MINT)?;program(t,&TOKEN2022)?;let(r,prior)=bookkeeping(cfg,inv)?;let before_v=volume(vol)?;let mut v=before_v.clone();check!(prior&1==0,7012);if prior==0{idle(&v)?;}else{check!(v.active==1&&v.nonce>0&&v.nonce<=v.seq&&v.origin<v.cleanup,7021);}
 for(ai,k)in [(cust,CUSTODY),(tax,TAX_AUTHORITY),(res,RESERVE),(settle,p::SETTLE_AUTHORITY),(wsol,p::WSOL_MINT),(ac,p::AMM_CONFIG),(auth,p::AMM_AUTHORITY),(pool,p::POOL),(hvault,p::VAULT_HTFP),(wvault,p::VAULT_WSOL),(obs,p::OBSERVATION)]{identity(ai,&k)?;}
 program(legacy,&LEGACY)?;program(sys,&SYSTEM)?;program(amm,&p::AMM)?;for ai in [m,cust,res,temp,payer,pool,hvault,wvault,obs]{required(ai,true,false)?;}required(payer,false,true)?;
 check!(system_zero(payer)&&system_zero(res)&&system_zero(tax)&&system_zero(settle),7001);canonical(b"htfp-settle-auth",&p::SETTLE_AUTHORITY)?;
 let wd=wsol.try_borrow_data()?;check!(wsol.owner==&LEGACY&&!wsol.executable&&wd.len()==82&&wd[44..46]==[9,1]&&u64_at(&wd,36)?==0&&option_key(&wd,0)?.is_none()&&option_key(&wd,46)?.is_none(),7023);let wsol_hash=hash(&wd).to_bytes();drop(wd);
 let ms=mint(m)?;let cs=custody(cust)?;check!(r<=cs.amount&&cs.amount<=ms.supply,7011);
 let mut expected_pool=pool_validate(pool,ac,obs)?;let hin=token(hvault,false)?;check!(hin.owner==p::AMM_AUTHORITY&&hin.state==1&&!hin.guard&&hin.delegate.is_none()&&hin.close.is_none()&&hin.allowance==0,7025);
 let hraw=hvault.try_borrow_data()?.to_vec();let wraw=wvault.try_borrow_data()?.to_vec();
    // CPMM prices from the SPL amount. A direct native credit has not entered that amount.
    let vault_wsol_before = native_wsol(wvault, &p::AMM_AUTHORITY)?;
    let x = effective(&expected_pool, hin.amount, 1)?;
    let y = effective(&expected_pool, vault_wsol_before.amount, 0)?;
 check!(ms.supply>0,7007);let q=u64_at(data,6)?;let(b,f)=split(q,r)?;
 let clock = Clock::get()?;
 #[cfg(not(feature = "production-volume-policy"))]
 let (time, available, remaining_credit) = volume_admission(f, x, v.credit, v.last, clock.unix_timestamp)?;
 #[cfg(feature = "production-volume-policy")]
 production_sale_admission(f, x)?;
 let next=v.seq.checked_add(1).ok_or(fail(7026))?;let sequence=v.seq.to_le_bytes();let(tkey,tb)=Pubkey::find_program_address(&[b"htfp-tmp-wsol",MINT.as_ref(),&sequence],&PROGRAM);identity(temp,&tkey)?;check!(system_zero(temp),7023);
 let(current,last,nonce)=tail(iv,false)?;if prior==0{idle(&v)?;check!(nonce==next,7021);v.active=1;v.origin=current;v.cleanup=last;v.nonce=nonce;}else{active(&v,current,last,nonce)?;}
 let p0=temp.lamports();let l=Rent::get()?.minimum_balance(165);let d=l.saturating_sub(p0);let w0=p0.saturating_sub(l);let res0=res.lamports();let payer0=payer.lamports();check!(payer0>=d,7023);
 let(native_tax,expected_output,protocol,fund,creator)=quote(f,x,y,clock.epoch)?;let close_total=checked_add(checked_add(p0,d)?,expected_output)?;checked_add(res0,close_total)?;
 let expected_obs=observation_expected(obs.try_borrow_data()?.to_vec(),clock.unix_timestamp as u64,y,x)?;
 write_volume(vol,&v)?;inventory_write(inv,r,3)?;
 let taxb=[bumps()?[2]];let tax_seeds:&[&[u8]]=&[b"htfp-tax-authority",MINT.as_ref(),&taxb];let mut burn=vec![15];burn.extend_from_slice(&b.to_le_bytes());burn.push(7);
 msg!("HTFP Process burn");invoke_signed(&native_ix(burn,vec![AccountMeta::new(CUSTODY,false),AccountMeta::new(MINT,false),AccountMeta::new_readonly(TAX_AUTHORITY,true)]),&[cust.clone(),m.clone(),tax.clone(),t.clone()],&[tax_seeds])?;
 let burned=mint(m)?;let mut cburn=cs.clone();cburn.amount=sub(cs.amount,b)?;check!(burned.supply==sub(ms.supply,b)?&&burned.withheld==ms.withheld&&custody(cust)?==cburn,7013);let mint_burn_bytes=m.try_borrow_data()?.to_vec();
 if d>0{invoke(&system_instruction::transfer(payer.key,temp.key,d),&[payer.clone(),temp.clone(),sys.clone()])?;}
 let tbb=[tb];let temp_seeds:&[&[u8]]=&[b"htfp-tmp-wsol",MINT.as_ref(),&sequence,&tbb];
 invoke_signed(&system_instruction::allocate(temp.key,165),&[temp.clone(),sys.clone()],&[temp_seeds])?;invoke_signed(&system_instruction::assign(temp.key,&LEGACY),&[temp.clone(),sys.clone()],&[temp_seeds])?;
 let mut init=vec![18];init.extend_from_slice(settle.key.as_ref());invoke(&Instruction{program_id:LEGACY,data:init,accounts:vec![AccountMeta::new(tkey,false),AccountMeta::new_readonly(p::WSOL_MINT,false)]},&[temp.clone(),wsol.clone(),legacy.clone()])?;check!(temporary_wsol_amount(temp,settle.key,l)?==w0&&temp.lamports()==checked_add(p0,d)?,7013);let temp_bytes=temp.try_borrow_data()?.to_vec();
 let mut swap=p::SWAP_DISCRIMINATOR.to_vec();swap.extend_from_slice(&f.to_le_bytes());swap.extend_from_slice(&0u64.to_le_bytes());
 let metas=vec![AccountMeta::new_readonly(TAX_AUTHORITY,true),AccountMeta::new_readonly(p::AMM_AUTHORITY,false),AccountMeta::new_readonly(p::AMM_CONFIG,false),AccountMeta::new(p::POOL,false),AccountMeta::new(CUSTODY,false),AccountMeta::new(tkey,false),AccountMeta::new(p::VAULT_HTFP,false),AccountMeta::new(p::VAULT_WSOL,false),AccountMeta::new_readonly(TOKEN2022,false),AccountMeta::new_readonly(LEGACY,false),AccountMeta::new_readonly(MINT,false),AccountMeta::new_readonly(p::WSOL_MINT,false),AccountMeta::new(p::OBSERVATION,false)];
 msg!("HTFP Process native swap");invoke_signed(&Instruction{program_id:p::AMM,data:swap,accounts:metas},&[tax.clone(),auth.clone(),ac.clone(),pool.clone(),cust.clone(),temp.clone(),hvault.clone(),wvault.clone(),t.clone(),legacy.clone(),m.clone(),wsol.clone(),obs.clone(),amm.clone()],&[tax_seeds])?;
 let output=sub(temporary_wsol_amount(temp,settle.key,l)?,w0)?;check!(output==expected_output&&temp.lamports()==checked_add(checked_add(p0,d)?,output)?,7013);let mut want_temp=temp_bytes;put(&mut want_temp,64,checked_add(w0,output)?);check!(&**temp.try_borrow_data()?==want_temp.as_slice(),7013);
 let mut cend=cs.clone();cend.amount=sub(cs.amount,q)?;check!(mint(m)?==burned&&custody(cust)?==cend&&*m.try_borrow_data()?==mint_burn_bytes.as_slice(),7013);
 let mut expected_hin=hin.clone();expected_hin.amount=checked_add(hin.amount,sub(f,native_tax)?)?;expected_hin.withheld=checked_add(hin.withheld,native_tax)?;check!(token(hvault,false)?==expected_hin,7013);
 let mut h_expected=hraw;put(&mut h_expected,64,checked_add(hin.amount,sub(f,native_tax)?)?);let fee_offset=extensions(&h_expected,2,false,false)?.fee_start;put(&mut h_expected,fee_offset,checked_add(hin.withheld,native_tax)?);check!(&**hvault.try_borrow_data()?==h_expected.as_slice(),7013);
 pool_validate(pool,ac,obs)?;
    let vault_wsol_after = native_wsol(wvault, &p::AMM_AUTHORITY)?;
    let mut w_expected = wraw;
    put(&mut w_expected, 64, sub(vault_wsol_before.amount, output)?);
    // Exact token bytes and unchanged surplus also prove the exact native debit.
    check!(&**wvault.try_borrow_data()? == w_expected.as_slice()
        && vault_wsol_after.surplus_lamports == vault_wsol_before.surplus_lamports, 7013);
 for(off,delta)in [(349,protocol),(365,fund),(405,creator)]{let n=checked_add(u64_at(&expected_pool,off)?,delta)?;put(&mut expected_pool,off,n);}put(&mut expected_pool,381,clock.epoch);
 check!(&**pool.try_borrow_data()?==expected_pool.as_slice()&&&**obs.try_borrow_data()?==expected_obs.as_slice()&&hash(&ac.try_borrow_data()?).to_bytes()==p::CONFIG_HASH,7013);
 let sb=[canonical(b"htfp-settle-auth",&p::SETTLE_AUTHORITY)?];msg!("HTFP Process close");invoke_signed(&Instruction{program_id:LEGACY,data:vec![9],accounts:vec![AccountMeta::new(tkey,false),AccountMeta::new(RESERVE,false),AccountMeta::new_readonly(p::SETTLE_AUTHORITY,true)]},&[temp.clone(),res.clone(),settle.clone(),legacy.clone()],&[&[b"htfp-settle-auth",MINT.as_ref(),&sb]])?;
 msg!("HTFP actual postclose owner={} data_len={} lamports={}",temp.owner,temp.data_len(),temp.lamports());check!(system_zero(temp)&&temp.lamports()==0,7024);check!(res.lamports()==checked_add(res0,close_total)?,7013);
 let rb=[bumps()?[4]];let reserve_seeds:&[&[u8]]=&[b"sol-vault",&rb];
 if d>0{msg!("HTFP Process refund D");invoke_signed(&system_instruction::transfer(res.key,payer.key,d),&[res.clone(),payer.clone(),sys.clone()],&[reserve_seeds])?;}
 check!(payer.lamports()==payer0&&res.lamports()==checked_add(checked_add(res0,p0)?,output)?,7013);
 if p0>0{msg!("HTFP Process restore P");invoke_signed(&system_instruction::transfer(res.key,temp.key,p0),&[res.clone(),temp.clone(),sys.clone()],&[reserve_seeds])?;}
 check!(system_zero(temp)&&temp.lamports()==p0&&res.lamports()==checked_add(res0,output)?&&custody(cust)?==cend&&mint(m)?==burned&&hash(&wsol.try_borrow_data()?).to_bytes()==wsol_hash,7013);
 #[cfg(not(feature = "production-volume-policy"))]
 {
     v.credit = remaining_credit;
     v.last = time;
 }
 v.seq=next;write_volume(vol,&v)?;inventory_write(inv,sub(r,q)?,2)?;
 let mut e=Vec::with_capacity(352);for k in [MINT,p::POOL,tkey,*payer.key,RESERVE]{e.extend_from_slice(k.as_ref());}e.extend_from_slice(&p::PROCESSING_COMMITMENT);
 for n in [before_v.seq,next,q,b,f,native_tax,sub(f,native_tax)?,x,output,p0,l,d,r,sub(r,q)?]{e.extend_from_slice(&n.to_le_bytes());}
 #[cfg(not(feature = "production-volume-policy"))]
 {
     for n in [before_v.credit, available, v.credit] { e.extend_from_slice(&n.to_le_bytes()); }
     e.extend_from_slice(&before_v.last.to_le_bytes());
     e.extend_from_slice(&v.last.to_le_bytes());
 }
 #[cfg(feature = "production-volume-policy")]
 e.extend_from_slice(&[0; 40]); // Reserved legacy quota positions.
 e.extend_from_slice(&nonce.to_le_bytes());event(3,&e);Ok(())
}

#[cfg(all(test, not(feature = "production-volume-policy")))]
mod host_tests {
 use super::*;
 #[test]
 fn binding_rejects_corruption_and_truncation(){
  assert_eq!(verify_binding(),Ok(()));
  for n in [0usize,16,1281]{assert_eq!(verify_binding_data(&p::PROCESSING_PREIMAGE[..n]),Err(fail(7018)));}
  let mut extra=p::PROCESSING_PREIMAGE.to_vec();extra.push(0);assert_eq!(verify_binding_data(&extra),Err(fail(7018)));
  for offset in [0usize,18,84,788,852,1048,1088,1184,1266]{let mut bad=p::PROCESSING_PREIMAGE;bad[offset]^=1;assert_eq!(verify_binding_data(&bad),Err(fail(7018)));}
 }
 #[test]
 fn split_and_native_fee_curve_boundaries(){
  for q in [8u64,16,800_000_000,8_000_000_000,1_600_000_000_000_000,u64::MAX&!7]{let(b,f)=split(q,q).unwrap();assert_eq!(b+f,q);assert_eq!(b/3,f/5);}
  for(q,r)in [(0,0),(1,1),(7,7),(9,9),(16,8),(u64::MAX,u64::MAX)]{assert_eq!(split(q,r),Err(fail(7006)));}
  let x=3_500_000_000_000_000_000u64;let y=8_800_000_000u64;
  assert_eq!(quote(1_000_000_000_000_000,x,y,1210).unwrap(),(80000000000000, 2300975, 276000000000, 92000000000, 2300000000000));
  assert_eq!(quote(1_000_000_000_000_000,x,y,1209).unwrap(),(0, 2501003, 300000000000, 100000000000, 2500000000000));
  for f in [1u64,12,13,99,100,10_000_000_000,u64::MAX]{
   let(tax,out,protocol,fund,creator)=quote(f,x,y,1210).unwrap();let numerator=u128::from(f)*800;
   assert!(u128::from(tax)*10_000>=numerator&&u128::from(tax.saturating_sub(1))*10_000<numerator);
   assert!(out<=y&&protocol<=f&&fund<=f&&creator<=f);
  }
 }
 #[test]
 fn shared_volume_cap_refill_and_backward_time(){
  let x=3_500_000_000_000_000_000;let cap=3_000_000_000_000_000u64;let gross=1_000_000_000_000_000u64;
  assert_eq!(p::C_BASE,gross);assert_eq!(p::CAPACITY_SCALED,cap);assert_eq!(p::REFILL_N,50_000_000_000_000);
  assert_eq!(volume_admission(gross,x,cap,100,100).unwrap(),(100,cap,0));
  assert_eq!(volume_admission(gross+1,x,cap,100,100),Err(fail(7020)));
  assert_eq!(volume_admission(1,x,cap+1,100,100),Err(fail(7019)));
  assert_eq!(volume_admission(1,999,cap,100,100),Err(fail(7020)));
  assert_eq!(volume_admission(1,1000,cap,100,100).unwrap().2,cap-3);
  assert_eq!(volume_admission(2,1000,cap,100,100),Err(fail(7020)));
  assert_eq!(volume_admission(1,x,10,100,99).unwrap(),(100,10,7));
  assert_eq!(volume_admission(gross,x,0,100,159),Err(fail(7020)));
  assert_eq!(volume_admission(gross,x,0,100,160).unwrap(),(160,cap,0));
  assert_eq!(volume_admission(1,x,0,i64::MIN,i64::MAX).unwrap(),(i64::MAX,cap,cap-3));
  let(_,_,first)=volume_admission(gross/2,x,cap,100,100).unwrap();
  let(_,_,second)=volume_admission(gross/2,x,first,100,100).unwrap();assert_eq!(second,0);
  assert_eq!(volume_admission(1,x,second,100,100),Err(fail(7020)));
 }
 #[test]
 fn effective_reserves_exclude_all_liabilities(){
  let mut data=[0u8;637];for side in [0usize,1]{
   put(&mut data,341+8*side,200);put(&mut data,357+8*side,3);put(&mut data,397+8*side,40);
   assert_eq!(effective(&data,1000,side),Ok(757));assert_eq!(effective(&data,243,side),Err(fail(7025)));
   put(&mut data,341+8*side,u64::MAX);put(&mut data,357+8*side,u64::MAX);assert_eq!(effective(&data,u64::MAX,side),Err(fail(7025)));
  }
 }
}

#[cfg(all(test, feature = "production-volume-policy"))]
mod production_policy_tests {
    use super::*;

    #[test]
    fn exact_gross_limit_and_floor() {
        for reserve in [1, 99, 100, 499, 500, 999, 1_000, 3_500_000_000_000_000_000, u64::MAX] {
            let maximum = reserve / 100;
            assert_eq!(production_sale_admission(maximum, reserve), Ok(()));
            assert_eq!(production_sale_admission(maximum + 1, reserve), Err(fail(7020)));
        }
        assert_eq!(production_sale_admission(u64::MAX, u64::MAX), Err(fail(7020)));
        assert_eq!(production_sale_admission(5, 499), Err(fail(7020)));
        assert_eq!(production_sale_admission(5, 500), Ok(()));
    }

    #[test]
    fn gross_admission_precedes_native_fee_and_preserves_inventory_split() {
        let booked = 16_000;
        let (burn, gross) = split(booked, booked).unwrap();
        assert_eq!((burn, gross), (6_000, 10_000));
        let (tax, ..) = quote(gross, 1_000_000, 1_000_000, p::ACTIVE_EPOCH).unwrap();
        assert_eq!(tax, 800);
        assert_eq!(production_sale_admission(gross, 1_000_000), Ok(()));
        assert_eq!(production_sale_admission(gross, 999_999), Err(fail(7020)));
        assert_eq!(production_sale_admission(gross - tax, 999_999), Ok(()));
        assert_eq!(split(booked, booked - 1), Err(fail(7006)));
        assert_eq!(split(0, booked), Err(fail(7006)));
        let maximum = u64::MAX & !7;
        let (burn, gross) = split(maximum, maximum).unwrap();
        assert_eq!(burn.checked_add(gross), Some(maximum));
    }

    #[test]
    fn retained_binding_is_distinct_and_valid() {
        assert_eq!(verify_binding(), Ok(()));
        assert_eq!(VOLUME_HEADER, (b"HTFPVOL2", 2));
        for offset in [0usize, 16, 18, 84, 1048, 1088, 1096, 1144, 1152, 1266] {
            let mut invalid = p::PROCESSING_PREIMAGE;
            invalid[offset] ^= 1;
            assert_eq!(verify_binding_data(&invalid), Err(fail(7018)));
        }
    }
}
