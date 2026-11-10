//! Reviewed artificial local processing profile; no caller-selected CPI or economics.
use super::*;
use crate::processing_profile as p;
use solana_program::{clock::Clock,instruction::get_stack_height,sysvar::instructions::{load_current_index_checked,load_instruction_at_checked}};
fn sub(a:u64,b:u64)->Res<u64>{a.checked_sub(b).ok_or(fail(7010))}
fn put(d:&mut[u8],off:usize,n:u64){d[off..off+8].copy_from_slice(&n.to_le_bytes());}
fn i64_at(d:&[u8],off:usize)->Res<i64>{Ok(i64::from_le_bytes(part(d,off,8)?.try_into().map_err(|_|fail(7019))?))}
fn u128_at(d:&[u8],off:usize)->Res<u128>{Ok(u128::from_le_bytes(part(d,off,16)?.try_into().map_err(|_|fail(7025))?))}
pub fn verify_binding()->ProgramResult{
 check!(hash(&p::PROCESSING_PREIMAGE).to_bytes()==p::PROCESSING_COMMITMENT,7018);
 let b=&p::PROCESSING_PREIMAGE;check!(b.len()==1282&&&b[..16]==b"HTFP_BOTH_LOC_V1"&&u16_at(b,16)?==1&&b[18..50]==COMMITMENT&&u16_at(b,50)?==25,7018);
 for(i,k)in p::ORDERED_KEYS.iter().enumerate(){check!(part(b,52+i*32,32)?==k.as_ref(),7018);}
 check!(p::PROGRAM==PROGRAM&&p::MINT==MINT&&p::CONFIG==CONFIG&&p::INVENTORY==INVENTORY&&p::TOKEN2022==TOKEN2022&&p::RESERVE==RESERVE&&p::TAX_AUTHORITY==TAX_AUTHORITY&&p::CUSTODY==CUSTODY&&p::GENESIS_OWNER==GENESIS_OWNER&&p::INITIALIZER==INITIALIZER&&p::GENESIS_HOLDING==GENESIS_HOLDING&&p::SYSTEM==SYSTEM&&p::LEGACY_TOKEN==LEGACY,7018);
 check!(part(b,852,32)?==[48, 169, 39, 61, 218, 23, 215, 179, 81, 56, 137, 175, 29, 171, 17, 133, 217, 250, 204, 71, 86, 166, 237, 243, 108, 66, 243, 11, 162, 40, 216, 209],7018);
 check!(part(b,884,4)?==[240, 244, 26, 0],7018);
 check!(part(b,888,8)?==[177, 143, 1, 31, 0, 0, 0, 0],7018);
 check!(part(b,896,32)?==[183, 129, 183, 29, 35, 10, 153, 16, 222, 77, 60, 16, 62, 114, 96, 143, 89, 127, 199, 60, 131, 238, 32, 114, 66, 172, 130, 183, 8, 56, 42, 106],7018);
 check!(part(b,928,4)?==[96, 217, 10, 0],7018);
 check!(part(b,932,8)?==[177, 143, 1, 31, 0, 0, 0, 0],7018);
 check!(part(b,940,32)?==[129, 144, 211, 247, 206, 182, 203, 122, 122, 141, 137, 36, 191, 248, 159, 159, 97, 30, 21, 206, 31, 128, 111, 43, 98, 55, 243, 49, 26, 152, 246, 151],7018);
 check!(part(b,972,4)?==[56, 168, 1, 0],7018);
 check!(part(b,976,8)?==[89, 155, 1, 31, 0, 0, 0, 0],7018);
 check!(part(b,984,32)?==[229, 231, 174, 209, 26, 211, 150, 158, 234, 42, 167, 108, 139, 77, 46, 115, 234, 37, 190, 126, 107, 92, 206, 152, 155, 119, 16, 207, 84, 82, 73, 110],7018);
 check!(part(b,1016,32)?==[100, 142, 19, 208, 46, 194, 232, 85, 93, 117, 30, 56, 152, 14, 1, 250, 165, 203, 180, 124, 46, 125, 114, 98, 243, 162, 16, 60, 170, 58, 250, 2],7018);
 check!(part(b,1048,32)?==[59, 92, 162, 243, 24, 114, 97, 204, 4, 142, 35, 83, 120, 146, 66, 6, 124, 58, 255, 25, 202, 182, 113, 104, 248, 109, 187, 210, 157, 153, 242, 28],7018);
 check!(part(b,1080,8)?==[1, 0, 0, 0, 0, 0, 0, 0],7018);
 check!(part(b,1088,8)?==[232, 3, 0, 0, 0, 0, 0, 0],7018);
 check!(part(b,1096,8)?==[0, 228, 11, 84, 2, 0, 0, 0],7018);
 check!(part(b,1104,8)?==[64, 75, 76, 0, 0, 0, 0, 0],7018);
 check!(part(b,1112,8)?==[3, 0, 0, 0, 0, 0, 0, 0],7018);
 check!(part(b,1120,8)?==[0, 241, 83, 101, 0, 0, 0, 0],7018);
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
 check!(part(b,1184,2)?==[22, 1],7018);
 check!(part(b,1186,2)?==[178, 0],7018);
 check!(part(b,1188,2)?==[125, 2],7018);
 check!(part(b,1190,2)?==[236, 0],7018);
 check!(part(b,1192,2)?==[235, 15],7018);
 check!(part(b,1194,4)?==[1, 3, 4, 5],7018);
 check!(part(b,1198,2)?==[1, 2],7018);
 check!(part(b,1200,32)?==[202, 72, 31, 78, 131, 137, 251, 209, 186, 121, 157, 137, 220, 50, 8, 152, 195, 70, 246, 17, 175, 150, 133, 118, 0, 32, 101, 140, 93, 225, 219, 123],7018);
 check!(part(b,1232,32)?==[135, 30, 221, 170, 109, 243, 221, 141, 255, 125, 173, 191, 226, 210, 119, 217, 93, 34, 8, 131, 140, 20, 75, 79, 88, 76, 16, 122, 199, 9, 75, 205],7018);
 check!(part(b,1264,2)?==[32, 3],7018);
 check!(part(b,1266,8)?==[9, 0, 0, 0, 0, 0, 0, 0],7018);
 check!(part(b,1274,8)?==[255, 255, 255, 255, 255, 255, 255, 255],7018);
 Ok(())
}
fn canonical(seed:&[u8],expected:&Pubkey)->Res<u8>{let(k,b)=Pubkey::find_program_address(&[seed,MINT.as_ref()],&PROGRAM);check!(k==*expected,7018);Ok(b)}
fn bookkeeping(cfg:&AccountInfo,inv:&AccountInfo)->Res<(u64,u8)>{
 identity(cfg,&CONFIG)?;identity(inv,&INVENTORY)?;required(inv,true,false)?;check!(cfg.owner==&PROGRAM&&inv.owner==&PROGRAM&&!cfg.executable&&!inv.executable,7001);
 check!(&**cfg.try_borrow_data()?==config_data(1)?.as_slice(),7002);let d=inv.try_borrow_data()?;
 check!(d.len()==20&&&d[..8]==b"HTFPINV1"&&u16_at(&d,8)?==1&&d[10]==bumps()?[1]&&d[11]<=3,7002);Ok((u64_at(&d,12)?,d[11]))
}
#[derive(Clone)]
struct Volume{credit:u64,last:i64,seq:u64,active:u8,origin:u16,cleanup:u16,nonce:u64}
fn volume(a:&AccountInfo)->Res<Volume>{
 identity(a,&p::VOLUME)?;required(a,true,false)?;check!(a.owner==&PROGRAM&&!a.executable&&a.data_len()==89,7019);let d=a.try_borrow_data()?;
 check!(&d[..8]==b"HTFPVOL1"&&u16_at(&d,8)?==1&&d[10]==canonical(b"htfp-volume",&p::VOLUME)? ,7019);check!(d[11..43]==p::PROCESSING_COMMITMENT,7018);
 let v=Volume{credit:u64_at(&d,43)?,last:i64_at(&d,51)?,seq:u64_at(&d,59)?,active:d[67],origin:u16_at(&d,68)?,cleanup:u16_at(&d,70)?,nonce:u64_at(&d,72)?};
 check!(v.credit<=30000000000&&v.active<=1&&d[80..].iter().all(|x|*x==0),7019);Ok(v)
}
fn write_volume(a:&AccountInfo,v:&Volume)->ProgramResult{
 let mut d=a.try_borrow_mut_data()?;check!(d.len()==89&&a.owner==&PROGRAM,7019);d.fill(0);d[..8].copy_from_slice(b"HTFPVOL1");d[8..10].copy_from_slice(&1u16.to_le_bytes());d[10]=canonical(b"htfp-volume",&p::VOLUME)?;d[11..43].copy_from_slice(&p::PROCESSING_COMMITMENT);
 put(&mut d,43,v.credit);d[51..59].copy_from_slice(&v.last.to_le_bytes());put(&mut d,59,v.seq);d[67]=v.active;d[68..70].copy_from_slice(&v.origin.to_le_bytes());d[70..72].copy_from_slice(&v.cleanup.to_le_bytes());put(&mut d,72,v.nonce);Ok(())
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
 let v=Volume{credit:30000000000,last:1700000000,seq:0,active:0,origin:0,cleanup:0,nonce:0};write_volume(vol,&v)?;inventory_write(inv,r,0)?;
 let mut e=Vec::with_capacity(120);e.extend_from_slice(MINT.as_ref());e.extend_from_slice(p::VOLUME.as_ref());e.extend_from_slice(&p::PROCESSING_COMMITMENT);e.extend_from_slice(&v.credit.to_le_bytes());e.extend_from_slice(&v.last.to_le_bytes());e.extend_from_slice(&v.seq.to_le_bytes());event(4,&e);Ok(())
}
pub fn finalize(a:&[AccountInfo],data:&[u8])->ProgramResult{
 check!(data.len()==14&&a.len()==4,7000);unique(a)?;let[cfg,inv,vol,iv]=a else{return Err(fail(7000));};let(r,g)=bookkeeping(cfg,inv)?;let mut v=volume(vol)?;check!(g&1==0,7012);let(cur,last,nonce)=tail(iv,true)?;check!(nonce==u64_at(data,6)?,7022);
 if g==0{idle(&v)?;check!(nonce==v.seq.checked_add(1).ok_or(fail(7026))?,7022);return Ok(());}
 active(&v,cur,last,nonce)?;v.active=0;v.origin=0;v.cleanup=0;v.nonce=0;write_volume(vol,&v)?;inventory_write(inv,r,0)?;
 let mut e=Vec::with_capacity(80);e.extend_from_slice(MINT.as_ref());e.extend_from_slice(p::VOLUME.as_ref());e.extend_from_slice(&nonce.to_le_bytes());e.extend_from_slice(&v.seq.to_le_bytes());event(5,&e);Ok(())
}
fn native_wsol(a:&AccountInfo,owner:&Pubkey,rent:Option<u64>)->Res<u64>{
 check!(a.owner==&LEGACY&&!a.executable&&a.data_len()==165,7023);let d=a.try_borrow_data()?;
 check!(key(&d,0)?==p::WSOL_MINT&&key(&d,32)?==*owner&&d[108]==1&&option_key(&d,72)?.is_none()&&option_key(&d,129)?.is_none()&&u64_at(&d,121)?==0&&u32_at(&d,109)?==1,7023);
 let l=u64_at(&d,113)?;if let Some(expected)=rent{check!(l==expected,7023);}let amount=u64_at(&d,64)?;check!(checked_add(amount,l)?==a.lamports(),7023);Ok(amount)
}
fn ceil(n:u128,d:u128)->Res<u64>{u64::try_from(n.checked_add(d-1).ok_or(fail(7010))?/d).map_err(|_|fail(7010))}
fn quote(f:u64,x:u64,y:u64,epoch:u64)->Res<(u64,u64,u64,u64,u64)>{
 let tax=if epoch>=9{ceil(u128::from(f).checked_mul(800).ok_or(fail(7010))?,10000)?}else{0};let input=sub(f,tax)?;
 let combined=ceil(u128::from(input).checked_mul(5000).ok_or(fail(7010))?,1000000)?;
 let creator=u64::try_from(u128::from(combined).checked_mul(2500).ok_or(fail(7010))?/5000).map_err(|_|fail(7010))?;
 let trade=sub(combined,creator)?;let curve=sub(input,combined)?;
 let numerator=u128::from(curve).checked_mul(u128::from(y)).ok_or(fail(7010))?;
 let denominator=u128::from(x).checked_add(u128::from(curve)).ok_or(fail(7010))?;
 let output=u64::try_from(numerator/denominator).map_err(|_|fail(7010))?;
 let protocol=u64::try_from(u128::from(trade).checked_mul(120000).ok_or(fail(7010))?/1000000).map_err(|_|fail(7010))?;
 let fund=u64::try_from(u128::from(trade).checked_mul(40000).ok_or(fail(7010))?/1000000).map_err(|_|fail(7010))?;
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
 let hraw=hvault.try_borrow_data()?.to_vec();let wraw=wvault.try_borrow_data()?.to_vec();let wa=native_wsol(wvault,&p::AMM_AUTHORITY,None)?;let x=effective(&expected_pool,hin.amount,1)?;let y=effective(&expected_pool,wa,0)?;
 check!(ms.supply>0,7007);let q=u64_at(data,6)?;check!(q>0&&q%8==0&&q<=r,7006);let b=(q/8)*3;let f=(q/8)*5;
 check!(u128::from(f)<=u128::from(x)/1000,7020);let clock=Clock::get()?;let time=clock.unix_timestamp.max(v.last);let elapsed=(i128::from(time)-i128::from(v.last))as u128;let available=(u128::from(v.credit)+elapsed.checked_mul(5000000).ok_or(fail(7010))?).min(30000000000)as u64;check!(u128::from(f)*3<=u128::from(available),7020);
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
 let mut init=vec![18];init.extend_from_slice(settle.key.as_ref());invoke(&Instruction{program_id:LEGACY,data:init,accounts:vec![AccountMeta::new(tkey,false),AccountMeta::new_readonly(p::WSOL_MINT,false)]},&[temp.clone(),wsol.clone(),legacy.clone()])?;check!(native_wsol(temp,settle.key,Some(l))?==w0&&temp.lamports()==checked_add(p0,d)?,7013);let temp_bytes=temp.try_borrow_data()?.to_vec();
 let mut swap=p::SWAP_DISCRIMINATOR.to_vec();swap.extend_from_slice(&f.to_le_bytes());swap.extend_from_slice(&0u64.to_le_bytes());
 let metas=vec![AccountMeta::new_readonly(TAX_AUTHORITY,true),AccountMeta::new_readonly(p::AMM_AUTHORITY,false),AccountMeta::new_readonly(p::AMM_CONFIG,false),AccountMeta::new(p::POOL,false),AccountMeta::new(CUSTODY,false),AccountMeta::new(tkey,false),AccountMeta::new(p::VAULT_HTFP,false),AccountMeta::new(p::VAULT_WSOL,false),AccountMeta::new_readonly(TOKEN2022,false),AccountMeta::new_readonly(LEGACY,false),AccountMeta::new_readonly(MINT,false),AccountMeta::new_readonly(p::WSOL_MINT,false),AccountMeta::new(p::OBSERVATION,false)];
 msg!("HTFP Process native swap");invoke_signed(&Instruction{program_id:p::AMM,data:swap,accounts:metas},&[tax.clone(),auth.clone(),ac.clone(),pool.clone(),cust.clone(),temp.clone(),hvault.clone(),wvault.clone(),t.clone(),legacy.clone(),m.clone(),wsol.clone(),obs.clone(),amm.clone()],&[tax_seeds])?;
 let output=sub(native_wsol(temp,settle.key,Some(l))?,w0)?;check!(output==expected_output&&temp.lamports()==checked_add(checked_add(p0,d)?,output)?,7013);let mut want_temp=temp_bytes;put(&mut want_temp,64,checked_add(w0,output)?);check!(&**temp.try_borrow_data()?==want_temp.as_slice(),7013);
 let mut cend=cs.clone();cend.amount=sub(cs.amount,q)?;check!(mint(m)?==burned&&custody(cust)?==cend&&*m.try_borrow_data()?==mint_burn_bytes.as_slice(),7013);
 let mut expected_hin=hin.clone();expected_hin.amount=checked_add(hin.amount,sub(f,native_tax)?)?;expected_hin.withheld=checked_add(hin.withheld,native_tax)?;check!(token(hvault,false)?==expected_hin,7013);
 let mut h_expected=hraw;put(&mut h_expected,64,checked_add(hin.amount,sub(f,native_tax)?)?);let fee_offset=extensions(&h_expected,2,false,false)?.fee_start;put(&mut h_expected,fee_offset,checked_add(hin.withheld,native_tax)?);check!(&**hvault.try_borrow_data()?==h_expected.as_slice(),7013);
 pool_validate(pool,ac,obs)?;
 let mut w_expected=wraw;put(&mut w_expected,64,sub(wa,output)?);check!(&**wvault.try_borrow_data()?==w_expected.as_slice()&&native_wsol(wvault,&p::AMM_AUTHORITY,None)?==sub(wa,output)?,7013);
 for(off,delta)in [(349,protocol),(365,fund),(405,creator)]{let n=checked_add(u64_at(&expected_pool,off)?,delta)?;put(&mut expected_pool,off,n);}put(&mut expected_pool,381,clock.epoch);
 check!(&**pool.try_borrow_data()?==expected_pool.as_slice()&&&**obs.try_borrow_data()?==expected_obs.as_slice()&&hash(&ac.try_borrow_data()?).to_bytes()==p::CONFIG_HASH,7013);
 let sb=[canonical(b"htfp-settle-auth",&p::SETTLE_AUTHORITY)?];msg!("HTFP Process close");invoke_signed(&Instruction{program_id:LEGACY,data:vec![9],accounts:vec![AccountMeta::new(tkey,false),AccountMeta::new(RESERVE,false),AccountMeta::new_readonly(p::SETTLE_AUTHORITY,true)]},&[temp.clone(),res.clone(),settle.clone(),legacy.clone()],&[&[b"htfp-settle-auth",MINT.as_ref(),&sb]])?;
 msg!("HTFP actual postclose owner={} data_len={} lamports={}",temp.owner,temp.data_len(),temp.lamports());check!(system_zero(temp)&&temp.lamports()==0,7024);check!(res.lamports()==checked_add(res0,close_total)?,7013);
 let rb=[bumps()?[4]];let reserve_seeds:&[&[u8]]=&[b"sol-vault",&rb];
 if d>0{msg!("HTFP Process refund D");invoke_signed(&system_instruction::transfer(res.key,payer.key,d),&[res.clone(),payer.clone(),sys.clone()],&[reserve_seeds])?;}
 check!(payer.lamports()==payer0&&res.lamports()==checked_add(checked_add(res0,p0)?,output)?,7013);
 if p0>0{msg!("HTFP Process restore P");invoke_signed(&system_instruction::transfer(res.key,temp.key,p0),&[res.clone(),temp.clone(),sys.clone()],&[reserve_seeds])?;}
 check!(system_zero(temp)&&temp.lamports()==p0&&res.lamports()==checked_add(res0,output)?&&custody(cust)?==cend&&mint(m)?==burned&&hash(&wsol.try_borrow_data()?).to_bytes()==wsol_hash,7013);
 v.credit=sub(available,f*3)?;v.last=time;v.seq=next;write_volume(vol,&v)?;inventory_write(inv,sub(r,q)?,2)?;
 let mut e=Vec::with_capacity(352);for k in [MINT,p::POOL,tkey,*payer.key,RESERVE]{e.extend_from_slice(k.as_ref());}e.extend_from_slice(&p::PROCESSING_COMMITMENT);
 for n in [before_v.seq,next,q,b,f,native_tax,sub(f,native_tax)?,x,output,p0,l,d,r,sub(r,q)?,before_v.credit,available,v.credit]{e.extend_from_slice(&n.to_le_bytes());}e.extend_from_slice(&before_v.last.to_le_bytes());e.extend_from_slice(&v.last.to_le_bytes());e.extend_from_slice(&nonce.to_le_bytes());event(3,&e);Ok(())
}
