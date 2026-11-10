//! Reviewed LOCAL-ONLY M3/BothToken profiles. Default build has no callable money profile.
//! No production profile, arbitrary CPI, authority editor or sweep endpoint.
#![allow(deprecated)]
use solana_program::{
    account_info::AccountInfo, entrypoint, entrypoint::ProgramResult, hash::{hash, hashv},
    instruction::{AccountMeta, Instruction}, log::sol_log_data, msg,
    program::{invoke, invoke_signed}, program_error::ProgramError, pubkey::Pubkey,
    rent::Rent, system_instruction, system_program, sysvar::{self, Sysvar},
};
#[cfg(all(feature="local-m3",feature="local-both"))]
compile_error!("local-m3 and local-both are mutually exclusive");
#[cfg(feature="local-both")]
mod processing_profile;
mod profile;
use profile::*;

const SUPPLY: u64 = 10_000_000_000_000_000_000;
const LEGACY: Pubkey = solana_program::pubkey!("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA");
const DOMAINS: [&[u8]; 4] = [b"htfp-config", b"htfp-inventory", b"htfp-tax-authority", b"htfp-tax-custody"];
type Res<T> = Result<T, ProgramError>;
macro_rules! check {
    ($condition:expr, $code:expr) => { if !($condition) { return Err(ProgramError::Custom($code)); } };
}
#[cfg(feature="local-both")]
mod processing;
fn fail(code: u32) -> ProgramError { ProgramError::Custom(code) }
fn part(d: &[u8], p: usize, n: usize) -> Res<&[u8]> { d.get(p..p.checked_add(n).ok_or(fail(7010))?).ok_or(fail(7002)) }
fn u16_at(d: &[u8], p: usize) -> Res<u16> { Ok(u16::from_le_bytes(part(d,p,2)?.try_into().map_err(|_|fail(7002))?)) }
fn u32_at(d: &[u8], p: usize) -> Res<u32> { Ok(u32::from_le_bytes(part(d,p,4)?.try_into().map_err(|_|fail(7002))?)) }
fn u64_at(d: &[u8], p: usize) -> Res<u64> { Ok(u64::from_le_bytes(part(d,p,8)?.try_into().map_err(|_|fail(7002))?)) }
fn key(d: &[u8], p: usize) -> Res<Pubkey> { Ok(Pubkey::new_from_array(part(d,p,32)?.try_into().map_err(|_|fail(7002))?)) }
fn option_key(d: &[u8], p: usize) -> Res<Option<Pubkey>> {
    // Native base COption: tag0 ignores inactive32 bytes, even when nonzero.
    match u32_at(d,p)? { 0 => { part(d,p+4,32)?; Ok(None) }, 1 => Ok(Some(key(d,p+4)?)), _ => Err(fail(7002)) }
}
fn checked_add(a:u64,b:u64)->Res<u64>{a.checked_add(b).ok_or(fail(7010))}
fn required(ai:&AccountInfo,w:bool,s:bool)->ProgramResult {
    check!(!w || ai.is_writable,7002); check!(!s || ai.is_signer,7005); Ok(())
}
fn system_zero(ai:&AccountInfo)->bool { *ai.owner==system_program::id() && ai.data_is_empty() && !ai.executable }
fn program(ai:&AccountInfo,expected:&Pubkey)->ProgramResult { check!(ai.key==expected && ai.executable,7001); Ok(()) }
fn identity(ai:&AccountInfo,k:&Pubkey)->ProgramResult { check!(ai.key==k,7001); Ok(()) }
fn unique(accounts:&[AccountInfo])->ProgramResult {
    for i in 0..accounts.len(){for j in 0..i {check!(accounts[i].key!=accounts[j].key,7003);}} Ok(())
}
fn protected(ai:&AccountInfo)->bool {
    [PROGRAM, MINT, TOKEN2022, SYSTEM, RESERVE, CONFIG, INVENTORY, TAX_AUTHORITY, CUSTODY].contains(ai.key)
        || ai.owner==&PROGRAM || ai.owner==&sysvar::id() || ai.executable
}
fn bumps()->Res<[u8;5]> {
    let expected=[CONFIG,INVENTORY,TAX_AUTHORITY,CUSTODY];
    let mut result=[0;5];
    for i in 0..4 { let (p,b)=Pubkey::find_program_address(&[DOMAINS[i],MINT.as_ref()],&PROGRAM);
        check!(p==expected[i],7001); result[i]=b; }
    let (p,b)=Pubkey::find_program_address(&[b"sol-vault"],&PROGRAM);
    check!(p==RESERVE,7001); result[4]=b; Ok(result)
}
fn verify_profile(id:&Pubkey)->ProgramResult {
    check!(cfg!(any(feature="local-m3",feature="local-both")),7015); check!(id==&PROGRAM,7001);
    check!(hash(&PREIMAGE).to_bytes()==COMMITMENT,7016);
    check!(&PREIMAGE[..16]==b"HTFP_M3_LOCAL_V1" && PREIMAGE[16..20]==[1,0,1,1],7016);
    let keys=[PROGRAM,MINT,TOKEN2022,SYSTEM,RESERVE,INITIALIZER,GENESIS_HOLDING,GENESIS_OWNER,CONFIG,INVENTORY,TAX_AUTHORITY,CUSTODY];
    for (i,k) in keys.iter().enumerate(){check!(&PREIMAGE[20+i*32..52+i*32]==k.as_ref(),7016);}
    check!(u64_at(&PREIMAGE,404)?==7 && PREIMAGE[412]==7 && u64_at(&PREIMAGE,413)?==SUPPLY,7016);
    check!(u16_at(&PREIMAGE,421)?==0 && u16_at(&PREIMAGE,423)?==800 && u64_at(&PREIMAGE,425)?==u64::MAX,7016);
    check!(&PREIMAGE[433..472]==[175,0,20,0,22,1,178,0,1,0,1,0,1,0,2,0,0,32,0,18,0,109,51,45,108,111,99,97,108,45,104,111,108,100,101,114,45,118,49],7016);
    check!(PREIMAGE[472..477]==bumps()?,7016);
    check!(Pubkey::create_with_seed(&INITIALIZER,"m3-local-holder-v1",&TOKEN2022).map_err(|_|fail(7016))?==GENESIS_HOLDING,7016);
    #[cfg(feature="local-both")]
    processing::verify_binding()?;
    Ok(())
}
// Strict bounded native TLV parser. Padding is accepted only when entirely zero.
// Fixed bookkeeping avoids consuming the SBF bump heap once per source/reload.
struct Extensions<'a> { fee:&'a[u8], fee_start:usize, guard:bool }
fn extensions<'a>(d:&'a[u8],kind:u8,mint:bool,minimal:bool)->Res<Extensions<'a>> {
    check!(d.len()>=166 && d[165]==kind,7002);
    if mint {check!(d[82..165].iter().all(|v|*v==0),7002);}
    let mut pos=166;let mut seen=[false;12];let mut count=0;
    let mut fee=None;let mut fee_start=0;let mut guard=false;
    while pos<d.len() {
        if d[pos..].iter().all(|v|*v==0){break;}
        let tag=u16_at(d,pos)?;let len=u16_at(d,pos+2)? as usize;pos+=4;
        let expected=if mint {match tag {1=>108,_=>return Err(fail(7004))}}
          else {match tag {2=>8,7 if !minimal=>0,8|11 if !minimal=>1,_=>return Err(fail(7004))}};
        check!(!seen[tag as usize] && len==expected,7004);seen[tag as usize]=true;count+=1;
        let value=part(d,pos,len)?;
        if tag==8 || tag==11 {check!(value[0]<=1,7002);}
        if tag==11 {guard=value[0]==1;}
        if tag==if mint{1}else{2} {fee=Some(value);fee_start=pos;}
        pos=pos.checked_add(len).ok_or(fail(7010))?;
    }
    if minimal || mint {check!(count==1 && d.len()==if mint{278}else{178},7004);}
    Ok(Extensions{fee:fee.ok_or(fail(7004))?,fee_start,guard})
}
#[derive(Clone,Debug,PartialEq,Eq)]
struct Mint { supply:u64, withheld:u64 }
fn mint(ai:&AccountInfo)->Res<Mint> {
    check!(ai.key==&MINT && ai.owner==&TOKEN2022 && !ai.executable,7001);
    let d=ai.try_borrow_data()?;
    check!(d.len()>=82 && d[44]==7 && d[45]==1,7002);
    check!(option_key(&d,0)?.is_none() && option_key(&d,46)?.is_none(),7016);
    let ex=extensions(&d,1,true,true)?;let fee=ex.fee;
    check!(fee[..32].iter().all(|v|*v==0) && key(fee,32)?==TAX_AUTHORITY,7016);
    check!(u64_at(fee,72)?==7 && u64_at(fee,80)?==u64::MAX && u16_at(fee,88)?==0,7016);
    check!(u64_at(fee,90)?==9 && u64_at(fee,98)?==u64::MAX && u16_at(fee,106)?==800,7016);
    let supply=u64_at(&d,36)?;check!(supply<=SUPPLY,7016);
    Ok(Mint{supply,withheld:u64_at(fee,64)?})
}
#[derive(Clone,Debug,PartialEq,Eq)]
struct Token {
    owner:Pubkey,amount:u64,withheld:u64,delegate:Option<Pubkey>,allowance:u64,
    close:Option<Pubkey>,state:u8,guard:bool,extension_digest:[u8;32],
}
fn token(ai:&AccountInfo,minimal:bool)->Res<Token> {
    check!(ai.owner==&TOKEN2022 && !ai.executable,7001);
    let d=ai.try_borrow_data()?; check!(d.len()>=166,7002);
    check!(key(&d,0)?==MINT,7001);
    check!(d[108]==1 || d[108]==2,7002);
    let native=u32_at(&d,109)?;check!(native<=1,7002);check!(native==0,7004);
    let ex=extensions(&d,2,false,minimal)?;
    let withheld=u64_at(ex.fee,0)?;let guard=ex.guard;
    // Hash exact passive TLV bytes including order/padding, zeroing only fee amount.
    let extension_digest=hashv(&[&d[166..ex.fee_start],&[0u8;8],&d[ex.fee_start+8..]]).to_bytes();
    Ok(Token{owner:key(&d,32)?,amount:u64_at(&d,64)?,withheld,delegate:option_key(&d,72)?,
        allowance:u64_at(&d,121)?,close:option_key(&d,129)?,state:d[108],guard,extension_digest})
}
fn custody(ai:&AccountInfo)->Res<Token> {
    identity(ai,&CUSTODY)?; let t=token(ai,true)?;
    check!(t.owner==TAX_AUTHORITY && t.state==1 && t.delegate.is_none() && t.close.is_none() && t.allowance==0,7002);Ok(t)
}
fn config_data(flag:u8)->Res<Vec<u8>>{
    let mut d=Vec::with_capacity(175);d.extend_from_slice(b"HTFPCFG1");d.extend_from_slice(&1u16.to_le_bytes());d.push(flag);
    d.extend_from_slice(&bumps()?[..4]);for k in [MINT,TOKEN2022,RESERVE,PROGRAM]{d.extend_from_slice(k.as_ref());}d.extend_from_slice(&COMMITMENT);Ok(d)
}
fn inventory_write(ai:&AccountInfo,r:u64,guard:u8)->ProgramResult{
    let mut d=ai.try_borrow_mut_data()?;check!(d.len()==20 && ai.owner==&PROGRAM,7002);
    d[..8].copy_from_slice(b"HTFPINV1");d[8..10].copy_from_slice(&1u16.to_le_bytes());d[10]=bumps()?[1];d[11]=guard;d[12..20].copy_from_slice(&r.to_le_bytes());Ok(())
}
fn common(cfg:&AccountInfo,inv:&AccountInfo,m:&AccountInfo,t:&AccountInfo)->Res<u64>{
    identity(cfg,&CONFIG)?;identity(inv,&INVENTORY)?;identity(m,&MINT)?;program(t,&TOKEN2022)?;
    required(inv,true,false)?;check!(cfg.owner==&PROGRAM && inv.owner==&PROGRAM && !cfg.executable && !inv.executable,7001);
    check!(&**cfg.try_borrow_data()?==config_data(1)?.as_slice(),7002);
    let d=inv.try_borrow_data()?;check!(d.len()==20 && &d[..8]==b"HTFPINV1" && u16_at(&d,8)?==1 && d[10]==bumps()?[1],7002);
    check!(d[11]<=if cfg!(feature="local-both"){3}else{1},7002);check!(d[11]&1==0,7012);u64_at(&d,12)
}
fn event(tag:u8,body:&[u8]){let mut d=b"HTFPEVT1".to_vec();d.extend_from_slice(&[1,tag]);d.extend_from_slice(body);sol_log_data(&[&d]);}
fn native_ix(data:Vec<u8>,accounts:Vec<AccountMeta>)->Instruction{Instruction{program_id:TOKEN2022,accounts,data}}
fn bootstrap<'a>(ai:&AccountInfo<'a>,payer:&AccountInfo<'a>,sys:&AccountInfo<'a>,len:usize,owner:&Pubkey,domain:&[u8],bump:u8)->ProgramResult{
    let required=Rent::get()?.minimum_balance(len);let top=required.saturating_sub(ai.lamports());
    let before=ai.lamports();
    if top>0{msg!("HTFP CPI storage top-up");invoke(&system_instruction::transfer(payer.key,ai.key,top),&[payer.clone(),ai.clone(),sys.clone()])?;}
    let bump_bytes=[bump];let seeds:&[&[u8]]=&[domain,MINT.as_ref(),&bump_bytes];
    msg!("HTFP CPI allocate");invoke_signed(&system_instruction::allocate(ai.key,len as u64),&[ai.clone(),sys.clone()],&[seeds])?;
    msg!("HTFP CPI assign");invoke_signed(&system_instruction::assign(ai.key,owner),&[ai.clone(),sys.clone()],&[seeds])?;
    check!(ai.owner==owner && ai.data_len()==len && ai.lamports()==checked_add(before,top)?,7013);Ok(())
}
fn initialize(a:&[AccountInfo])->ProgramResult{
    check!(a.len()==10,7000);
    let [cfg,inv,m,cust,tax,res,g,i,t,sys]=a else{return Err(fail(7000));};
    for (ai,k) in [(cfg,CONFIG),(inv,INVENTORY),(m,MINT),(cust,CUSTODY),(tax,TAX_AUTHORITY),(res,RESERVE),(g,GENESIS_HOLDING),(i,INITIALIZER)]{identity(ai,&k)?;}
    unique(a)?;check!(a.iter().all(|x|x.key!=&PROGRAM && x.owner!=&sysvar::id()),7003);
    program(t,&TOKEN2022)?;program(sys,&SYSTEM)?;
    for ai in [cfg,inv,cust,i]{required(ai,true,false)?;}
    required(i,false,true)?;check!(system_zero(i) && system_zero(tax) && system_zero(res),7001);
    for ai in [cfg,inv,cust]{check!(system_zero(ai),7017);}
    let ms=mint(m)?;let gs=token(g,true)?;
    check!(ms.supply==SUPPLY && ms.withheld==0 && gs.amount==SUPPLY && gs.withheld==0 &&
        gs.owner==GENESIS_OWNER && gs.delegate.is_none() && gs.close.is_none() && gs.allowance==0 && gs.state==1,7016);
    let m_before=m.try_borrow_data()?.to_vec();let g_before=g.try_borrow_data()?.to_vec();
    let immutable_balances=[m.lamports(),g.lamports(),res.lamports(),tax.lamports()];
    let b=bumps()?;let payer_before=i.lamports();
    let storage=checked_add(checked_add(Rent::get()?.minimum_balance(175).saturating_sub(cfg.lamports()),Rent::get()?.minimum_balance(20).saturating_sub(inv.lamports()))?,Rent::get()?.minimum_balance(178).saturating_sub(cust.lamports()))?;
    // Reviewed fresh-init exception: only Config then Inventory System CPIs precede guard.
    bootstrap(cfg,i,sys,175,&PROGRAM,DOMAINS[0],b[0])?;
    bootstrap(inv,i,sys,20,&PROGRAM,DOMAINS[1],b[1])?;
    cfg.try_borrow_mut_data()?.copy_from_slice(&config_data(0)?);
    inventory_write(inv,0,1)?;
    msg!("HTFP init guard installed");
    // Guard exists before ALL Custody System/native calls.
    bootstrap(cust,i,sys,178,&TOKEN2022,DOMAINS[3],b[3])?;
    let mut data=vec![18];data.extend_from_slice(TAX_AUTHORITY.as_ref());
    msg!("HTFP CPI initialize custody");
    invoke(&native_ix(data,vec![AccountMeta::new(CUSTODY,false),AccountMeta::new_readonly(MINT,false)]),&[cust.clone(),m.clone(),t.clone()])?;
    let cs=custody(cust)?;check!(cs.amount==0 && cs.withheld==0,7013);
    check!(mint(m)?==ms && token(g,true)?==gs && *m.try_borrow_data()?==m_before.as_slice() && *g.try_borrow_data()?==g_before.as_slice(),7013);
    check!([m.lamports(),g.lamports(),res.lamports(),tax.lamports()]==immutable_balances,7013);
    check!(payer_before.checked_sub(i.lamports())==Some(storage),7013);
    cfg.try_borrow_mut_data()?.copy_from_slice(&config_data(1)?);inventory_write(inv,0,0)?;
    let mut out=vec![1];out.extend_from_slice(&COMMITMENT);out.extend_from_slice(MINT.as_ref());out.extend_from_slice(RESERVE.as_ref());event(0,&out);Ok(())
}
fn recover(a:&[AccountInfo],data:&[u8])->ProgramResult{
    check!(data.len()==8,7000);let n=u16_at(data,6)? as usize;check!(n<=32 && a.len()==6+n,7000);
    let (fixed,sources)=a.split_at(6);let [cfg,inv,m,cust,tax,t]=fixed else{return Err(fail(7000));};
    let r=common(cfg,inv,m,t)?;
    #[cfg(feature="local-both")]
    check!(inv.try_borrow_data()?[11]&2==0,7021);
    identity(cust,&CUSTODY)?;identity(tax,&TAX_AUTHORITY)?;
    unique(fixed)?;required(m,true,false)?;required(cust,true,false)?;check!(system_zero(tax),7001);
    let ms=mint(m)?;let cs=custody(cust)?;check!(r<=cs.amount,7011);
    let mut prior:Vec<(&AccountInfo,Token)>=Vec::with_capacity(n);let mut absent=0u16;let mut zero=0u16;
    for (j,source) in sources.iter().enumerate(){
        required(source,true,false)?;
        check!(!protected(source) && !sources[..j].iter().any(|x|x.key==source.key),7003);
        if system_zero(source) && source.lamports()==0{absent+=1;continue;}
        let state=token(source,false).map_err(|_|fail(7014))?;
        if state.withheld==0{zero+=1;}
        prior.push((source,state));
    }
    let mut expected=checked_add(ms.withheld,cs.withheld)?;
    for (_,state) in &prior{expected=checked_add(expected,state.withheld)?;}
    inventory_write(inv,r,1)?;
    let mut metas=Vec::with_capacity(n+2);metas.push(AccountMeta::new(MINT,false));
    let mut infos=Vec::with_capacity(n+3);infos.push(m.clone());
    if cs.withheld>0{metas.push(AccountMeta::new(CUSTODY,false));infos.push(cust.clone());}
    for (source,state) in &prior{if state.withheld>0{metas.push(AccountMeta::new(*source.key,false));infos.push((*source).clone());}}
    if metas.len()>1{infos.push(t.clone());msg!("HTFP CPI harvest");invoke(&native_ix(vec![26,4],metas),&infos)?;}
    let harvested=mint(m)?;check!(harvested.supply==ms.supply && harvested.withheld==expected,7011);
    let mut cleared=cs.clone();cleared.withheld=0;check!(custody(cust)?==cleared,7011);
    for (source,state) in &prior{let mut want=state.clone();want.withheld=0;check!(token(source,false)?==want,7011);}
    if expected>0{
        let bb=[bumps()?[2]];let seeds:&[&[u8]]=&[DOMAINS[2],MINT.as_ref(),&bb];
        msg!("HTFP CPI withdraw mint withholding");
        invoke_signed(&native_ix(vec![26,2],vec![AccountMeta::new(MINT,false),AccountMeta::new(CUSTODY,false),AccountMeta::new_readonly(TAX_AUTHORITY,true)]),&[m.clone(),cust.clone(),tax.clone(),t.clone()],&[seeds])?;
    }
    let after=custody(cust)?;let end=mint(m)?;
    check!(end.supply==ms.supply && end.withheld==0 && after.withheld==0,7011);
    let delta=after.amount.checked_sub(cs.amount).ok_or(fail(7011))?;check!(delta==expected,7011);
    cleared.amount=checked_add(cs.amount,delta)?;check!(after==cleared,7011);
    let next=checked_add(r,delta)?;check!(next<=after.amount,7011);inventory_write(inv,next,0)?;
    let mut out=Vec::new();for k in [MINT,CUSTODY]{out.extend_from_slice(k.as_ref());}for v in [delta,r,next]{out.extend_from_slice(&v.to_le_bytes());}
    for v in [n as u16,absent,zero]{out.extend_from_slice(&v.to_le_bytes());}event(1,&out);Ok(())
}
fn authorize(source:&Token,authority:&AccountInfo,signers:&[AccountInfo],kind:u8)->ProgramResult{
    check!(source.owner==*authority.key,7005);
    // Native multisig classification precedes ordinary owner/PDA signer handling.
    // A signature by the account address never substitutes for its member threshold.
    let native_multisig=(*authority.owner==TOKEN2022 || *authority.owner==LEGACY) && authority.data_len()==355;
    if kind==0{check!(!native_multisig && signers.is_empty() && authority.is_signer,7005);return Ok(());}
    check!(kind==1 && !signers.is_empty() && signers.len()<=11,7000);
    check!(native_multisig && !authority.executable,7005);
    let d=authority.try_borrow_data()?;let m=d[0] as usize;let n=d[1] as usize;
    check!(d[2]==1 && m>=1 && m<=n && n<=11,7005);
    let mut matched=[false;11];let mut count=0;
    for (i,s) in signers.iter().enumerate(){
        check!(s.is_signer,7005);check!(!signers[..i].iter().any(|p|p.key==s.key) && s.key!=authority.key,7003);
        let mut member=false;
        for j in 0..n{if key(&d,3+j*32)?==*s.key{member=true;if !matched[j]{matched[j]=true;count+=1;}}}
        check!(member,7005);
    }
    check!(count>=m,7005);Ok(())
}
fn redeem(a:&[AccountInfo],data:&[u8])->ProgramResult{
    check!(data.len()==56,7000);let amount=u64_at(data,6)?;let minimum=u64_at(data,14)?;let recipient=key(data,22)?;let kind=data[54];let n=data[55] as usize;
    check!(kind<=1 && (kind!=0 || n==0) && n<=11 && a.len()==9+n,7000);
    let (fixed,signers)=a.split_at(9);let [cfg,inv,m,source,res,payee,authority,t,sys]=fixed else{return Err(fail(7000));};
    let r=common(cfg,inv,m,t)?;let prior_guard=inv.try_borrow_data()?[11];identity(res,&RESERVE)?;program(sys,&SYSTEM)?;
    check!(system_zero(res),7001);for ai in [m,source,res,payee]{required(ai,true,false)?;}
    check!(!protected(source) && !protected(payee) && !protected(authority),7003);
    for signer in signers {check!(!protected(signer),7003);}
    // The permitted external source/authority/signer/payee aliases retain exact owner/signature validation.
    let ms=mint(m)?;let src=token(source,false)?;
    check!(src.state==1 && !src.guard,7004);
    check!(recipient==*payee.key,7005);authorize(&src,authority,signers,kind)?;
    check!(ms.supply>0,7007);check!(amount>0 && amount<=src.amount && src.amount<=ms.supply,7006);
    let maintenance=Rent::get()?.minimum_balance(0);let reserve_before=res.lamports();let v=reserve_before.saturating_sub(maintenance);
    let payout=(u128::from(v).checked_mul(u128::from(amount)).ok_or(fail(7010))?/u128::from(ms.supply)) as u64;
    check!(payout>0,7008);check!(payout>=minimum,7009);
    let payee_before=payee.lamports();let source_lamports=source.lamports();inventory_write(inv,r,prior_guard|1)?;
    let mut burn_data=vec![15];burn_data.extend_from_slice(&amount.to_le_bytes());burn_data.push(7);
    let mut metas=vec![AccountMeta::new(*source.key,false),AccountMeta::new(MINT,false),AccountMeta::new_readonly(*authority.key,kind==0)];
    let mut infos=vec![source.clone(),m.clone(),authority.clone()];
    for signer in signers{metas.push(AccountMeta::new_readonly(*signer.key,true));infos.push(signer.clone());}
    infos.push(t.clone());msg!("HTFP CPI burn authorized redemption");invoke(&native_ix(burn_data,metas),&infos)?;
    let after_mint=mint(m)?;let after_source=token(source,false)?;
    let mut want=src.clone();want.amount=want.amount.checked_sub(amount).ok_or(fail(7010))?;
    if src.delegate==Some(*authority.key){
        want.allowance=src.allowance.checked_sub(amount).ok_or(fail(7013))?;
        if want.allowance==0{want.delegate=None;}
    }
    check!(after_mint.supply==ms.supply.checked_sub(amount).ok_or(fail(7010))? && after_mint.withheld==ms.withheld && after_source==want,7013);
    let bb=[bumps()?[4]];let seeds:&[&[u8]]=&[b"sol-vault",&bb];
    msg!("HTFP CPI native redemption payout");
    invoke_signed(&system_instruction::transfer(&RESERVE,payee.key,payout),&[res.clone(),payee.clone(),sys.clone()],&[seeds])?;
    check!(reserve_before.checked_sub(res.lamports())==Some(payout) && payee.lamports().checked_sub(payee_before)==Some(payout) && res.lamports()>=maintenance,7013);
    check!(mint(m)?==after_mint && token(source,false)?==after_source,7013);
    if source.key!=payee.key{check!(source.lamports()==source_lamports,7013);}
    inventory_write(inv,r,prior_guard)?;
    let mut out=Vec::new();for k in [MINT,*source.key,*authority.key,*payee.key]{out.extend_from_slice(k.as_ref());}
    for val in [amount,minimum,ms.supply,v,maintenance,payout,after_mint.supply]{out.extend_from_slice(&val.to_le_bytes());}event(2,&out);Ok(())
}
entrypoint!(process_instruction);
pub fn process_instruction(id:&Pubkey,accounts:&[AccountInfo],data:&[u8])->ProgramResult{
    check!(data.len()>=6 && &data[..4]==b"HTFP" && data[4]==1 && data[5]<=if cfg!(feature="local-both"){5}else{3},7000);
    verify_profile(id)?;
    match data[5] {0=>{check!(data.len()==6,7000);initialize(accounts)},1=>recover(accounts,data),2=>redeem(accounts,data),#[cfg(feature="local-both")] 3=>processing::process(accounts,data),#[cfg(feature="local-both")] 4=>{check!(data.len()==6,7000);processing::initialize_processing(accounts)},#[cfg(feature="local-both")] 5=>processing::finalize(accounts,data),_=>Err(fail(7015))}
}
