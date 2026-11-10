#![allow(unexpected_cfgs, deprecated)]
mod constants;
use constants::*;
use solana_program::{account_info::AccountInfo,entrypoint,entrypoint::ProgramResult,program_error::ProgramError,
 instruction::{AccountMeta,Instruction,get_stack_height},program::{invoke,invoke_signed},pubkey::Pubkey,
 rent::Rent,system_instruction,sysvar::{self,Sysvar,instructions::{load_current_index_checked,load_instruction_at_checked}},log::sol_log_data};
type Res<T>=Result<T,ProgramError>;
fn err(n:u32)->ProgramError{ProgramError::Custom(n)}
macro_rules! need {($e:expr,$n:expr)=>{if !$e{return Err(err($n));}}}
fn u64at(d:&[u8],p:usize)->Res<u64>{Ok(u64::from_le_bytes(d.get(p..p+8).ok_or(err(8102))?.try_into().map_err(|_|err(8102))?))}
fn u16at(d:&[u8],p:usize)->Res<u16>{Ok(u16::from_le_bytes(d.get(p..p+2).ok_or(err(8102))?.try_into().map_err(|_|err(8102))?))}
fn put64(d:&mut[u8],p:usize,v:u64){d[p..p+8].copy_from_slice(&v.to_le_bytes());}
fn add(a:u64,b:u64)->Res<u64>{a.checked_add(b).ok_or(err(8109))}
fn sub(a:u64,b:u64)->Res<u64>{a.checked_sub(b).ok_or(err(8109))}
fn zero(a:&AccountInfo)->bool{a.owner==&SYSTEM && a.data_len()==0 && !a.executable}
fn key(a:&AccountInfo,k:&Pubkey,w:bool,s:bool)->ProgramResult{need!(a.key==k && (!w||a.is_writable)&&(!s||a.is_signer),8101);Ok(())}
fn executable(a:&AccountInfo,k:&Pubkey)->ProgramResult{key(a,k,false,false)?;need!(a.executable,8101);Ok(())}
fn controller(a:&AccountInfo,w:bool)->ProgramResult{key(a,&INITIALIZER,w,true)?;need!(zero(a),8101);Ok(())}
fn unique(a:&[AccountInfo])->ProgramResult{for(i,x)in a.iter().enumerate(){need!(!a[..i].iter().any(|y|y.key==x.key),8103);}Ok(())}
fn pda(seed:&[u8])->(Pubkey,u8){Pubkey::find_program_address(&[seed,MINT.as_ref()],&PROOF_PROGRAM)}
fn state(a:&AccountInfo,k:&Pubkey,len:usize,magic:&[u8],seed:&[u8])->ProgramResult{
 key(a,k,true,false)?;need!(a.owner==&PROOF_PROGRAM&&!a.executable&&a.data_len()==len,8102);
 let d=a.try_borrow_data()?;need!(&d[..8]==magic&&u16at(&d,8)?==1&&d[10]==pda(seed).1,8102);
 if len!=20{need!(d[11..43]==BINDING || len==256&&d[12..44]==BINDING,8102);}Ok(())
}
fn states(g:&AccountInfo,v:&AccountInfo,r:&AccountInfo)->ProgramResult{
 state(g,&PROOF_GUARD,20,b"M4BGRD01",b"m4b-proof-guard")?;
 state(v,&PROOF_VOLUME,89,b"HTFPVOL1",b"m4b-proof-volume")?;
 state(r,&PROOF_RECORD,256,b"M4BSET01",b"m4b-proof-record")?;
 let gd=g.try_borrow_data()?;need!(gd[11]<=3,8102);
 let vd=v.try_borrow_data()?;let rd=r.try_borrow_data()?;
 need!(vd[80..].iter().all(|x|*x==0)&&vd[67]<=1&&u64at(&vd,43)?==30000000000&&u64at(&vd,51)?==1700000000,8102);
 need!(rd[11]<=2&&rd[204..].iter().all(|x|*x==0),8102);
 if rd[11]==0{need!(rd[44..].iter().all(|x|*x==0),8102);}
 Ok(())
}
fn guard(g:&AccountInfo)->Res<u8>{let d=g.try_borrow_data()?;let x=d[11];need!(x<=3,8102);need!(x&1==0,8104);Ok(x)}
fn setguard(g:&AccountInfo,x:u8)->ProgramResult{g.try_borrow_mut_data()?[11]=x;Ok(())}
fn inactive(v:&AccountInfo)->ProgramResult{let d=v.try_borrow_data()?;need!(d[67..80].iter().all(|x|*x==0),8105);Ok(())}
fn sysvar(a:&AccountInfo)->ProgramResult{key(a,&INSTRUCTIONS_SYSVAR,false,false)?;need!(!a.executable&&!a.is_writable&&a.owner==&sysvar::ID&&a.data_len()>=4,8101);Ok(())}
fn tail(a:&AccountInfo,finishing:bool)->Res<(u16,u16,u64)>{
 sysvar(a)?;let count={let d=a.try_borrow_data()?;u16at(&d,0)?};let current=load_current_index_checked(a)?;
 need!(count>0&&current<count,8106);let last=count-1;
 if finishing{need!(current==last&&get_stack_height()==1,8106);}else{need!(count>=2&&current<last,8105);}
 let ix=load_instruction_at_checked(last as usize,a)?;
 need!(ix.program_id==PROOF_PROGRAM&&ix.data.len()==17&&&ix.data[..8]==b"M4BPRF01"&&ix.data[8]==6&&ix.accounts.len()==5,8106);
 for(i,k)in [INITIALIZER,PROOF_GUARD,PROOF_VOLUME,PROOF_RECORD,INSTRUCTIONS_SYSVAR].iter().enumerate(){
  let m=&ix.accounts[i];need!(m.pubkey==*k,8106);if i==0{need!(m.is_signer,8106);}if (1..=3).contains(&i){need!(m.is_writable,8106);}if i==4{need!(!m.is_writable,8106);}
 }
 Ok((current,last,u64at(&ix.data,9)?))
}
fn active(v:&AccountInfo,current:u16,last:u16,nonce:u64)->ProgramResult{
 let d=v.try_borrow_data()?;need!(d[67]==1&&u16at(&d,68)?<=current&&current<=last&&u16at(&d,68)?<last&&u16at(&d,70)?==last&&u64at(&d,72)?==nonce&&nonce>0&&nonce<=u64at(&d,59)?,8105);Ok(())
}
fn native_transfer<'a>(from:&AccountInfo<'a>,to:&AccountInfo<'a>,sys:&AccountInfo<'a>,amount:u64,seeds:Option<&[&[u8]]>)->ProgramResult{
 if amount==0{return Ok(());}let ix=system_instruction::transfer(from.key,to.key,amount);
 let infos=[from.clone(),to.clone(),sys.clone()];match seeds{Some(s)=>invoke_signed(&ix,&infos,&[s]),None=>invoke(&ix,&infos)}
}
fn allocate<'a>(a:&AccountInfo<'a>,payer:&AccountInfo<'a>,sys:&AccountInfo<'a>,len:usize,owner:&Pubkey,seeds:&[&[u8]])->ProgramResult{
 need!(zero(a),8102);let before=a.lamports();let deposit=Rent::get()?.minimum_balance(len).saturating_sub(before);
 native_transfer(payer,a,sys,deposit,None)?;
 invoke_signed(&system_instruction::allocate(a.key,len as u64),&[a.clone(),sys.clone()],&[seeds])?;
 invoke_signed(&system_instruction::assign(a.key,owner),&[a.clone(),sys.clone()],&[seeds])?;
 need!(a.owner==owner&&a.data_len()==len&&a.lamports()==add(before,deposit)?,8107);Ok(())
}
fn emit(tag:u8,body:&[u8]){let mut out=b"M4BPEV01".to_vec();out.extend_from_slice(&[1,tag]);out.extend_from_slice(body);sol_log_data(&[&out]);}
fn bootstrap(a:&[AccountInfo])->ProgramResult{
 need!(a.len()==7,8100);unique(a)?;let[c,g,v,r,res,mark,sys]=a else{return Err(err(8100));};controller(c,true)?;executable(sys,&SYSTEM)?;
 for(ai,k)in [(g,PROOF_GUARD),(v,PROOF_VOLUME),(r,PROOF_RECORD),(res,PROOF_RESERVE),(mark,PROOF_MARKER)]{key(ai,&k,true,false)?;need!(zero(ai),8102);}
 for(ai,len,magic,seed)in [(g,20,b"M4BGRD01",b"m4b-proof-guard".as_slice()),(v,89,b"HTFPVOL1",b"m4b-proof-volume".as_slice()),(r,256,b"M4BSET01",b"m4b-proof-record".as_slice())]{
  let bump=[pda(seed).1];allocate(ai,c,sys,len,&PROOF_PROGRAM,&[seed,MINT.as_ref(),&bump])?;
  let mut d=ai.try_borrow_mut_data()?;d.fill(0);d[..8].copy_from_slice(magic);d[8..10].copy_from_slice(&1u16.to_le_bytes());d[10]=bump[0];
  if len==89{d[11..43].copy_from_slice(&BINDING);put64(&mut d,43,30000000000);put64(&mut d,51,1700000000);}
  if len==256{d[12..44].copy_from_slice(&BINDING);}
 }
 for ai in [res,mark]{native_transfer(c,ai,sys,Rent::get()?.minimum_balance(0).saturating_sub(ai.lamports()),None)?;}
 states(g,v,r)
}
fn probe(a:&[AccountInfo],tag:u8,payload:u8)->ProgramResult{
 need!(a.len()==if tag==7{9}else{7},8100);unique(a)?;
 let(c,g,v,r,mark,iv,sys)=(&a[0],&a[1],&a[2],&a[3],&a[4],&a[5],&a[6]);controller(c,true)?;states(g,v,r)?;key(mark,&PROOF_MARKER,true,false)?;need!(zero(mark),8101);executable(sys,&SYSTEM)?;sysvar(iv)?;
 let prior=guard(g)?;
 if tag==8{return Err(err(8108));}
 if tag==2{need!(prior==0,8105);inactive(v)?;setguard(g,1)?;native_transfer(c,mark,sys,1,None)?;let before={let d=g.try_borrow_data()?;u64at(&d,12)?};put64(&mut g.try_borrow_mut_data()?,12,add(before,1)?);return setguard(g,0);}
 if tag==3{if prior==0{inactive(v)?;}setguard(g,prior|1)?;native_transfer(c,mark,sys,1,None)?;return setguard(g,prior);}
 need!(r.try_borrow_data()?[11]!=1,8107);let(current,last,nonce)=tail(iv,false)?;
 let seq={let d=v.try_borrow_data()?;u64at(&d,59)?};let next=add(seq,1)?;
 if prior==0{inactive(v)?;need!(nonce==next,8105);let mut d=v.try_borrow_mut_data()?;d[67]=1;d[68..70].copy_from_slice(&current.to_le_bytes());d[70..72].copy_from_slice(&last.to_le_bytes());put64(&mut d,72,nonce);}else{active(v,current,last,nonce)?;}
 setguard(g,3)?;native_transfer(c,mark,sys,1,None)?;
 if tag==1{need!(payload<=1,8100);if payload==1{return Err(err(8108));}}
 if tag==7{
  need!(payload<=2,8100);executable(&a[7],&PROOF_PROGRAM)?;executable(&a[8],&WALLET_PROGRAM)?;
  if payload==0{let mut data=b"M4BPRF01".to_vec();data.push(2);let metas=probe_metas();invoke(&Instruction{program_id:PROOF_PROGRAM,accounts:metas,data},a)?;}
  else{let mut data=b"M4BWAL01".to_vec();data.push(if payload==1{8}else{5});data.extend_from_slice(&nonce.to_le_bytes());let accounts=wallet_metas();invoke(&Instruction{program_id:WALLET_PROGRAM,accounts,data},a)?;}
 }
 put64(&mut v.try_borrow_mut_data()?,59,next);setguard(g,2)?;let mut event=seq.to_le_bytes().to_vec();event.extend_from_slice(&next.to_le_bytes());event.push(2);emit(1,&event);Ok(())
}
fn probe_metas()->Vec<AccountMeta>{vec![AccountMeta::new(INITIALIZER,true),AccountMeta::new(PROOF_GUARD,false),AccountMeta::new(PROOF_VOLUME,false),AccountMeta::new(PROOF_RECORD,false),AccountMeta::new(PROOF_MARKER,false),AccountMeta::new_readonly(INSTRUCTIONS_SYSVAR,false),AccountMeta::new_readonly(SYSTEM,false)]}
fn wallet_metas()->Vec<AccountMeta>{let mut m=probe_metas();m.push(AccountMeta::new_readonly(PROOF_PROGRAM,false));m.push(AccountMeta::new_readonly(WALLET_PROGRAM,false));m}
fn finalizer(a:&[AccountInfo],nonce:u64)->ProgramResult{
 need!(a.len()==5,8100);unique(a)?;let[c,g,v,r,iv]=a else{return Err(err(8100));};controller(c,false)?;states(g,v,r)?;let prior=guard(g)?;let(current,last,tailnonce)=tail(iv,true)?;need!(tailnonce==nonce,8106);
 if prior==0{inactive(v)?;let d=v.try_borrow_data()?;need!(nonce==add(u64at(&d,59)?,1)?&&r.try_borrow_data()?[11]==0,8106);return Ok(());}
 active(v,current,last,nonce)?;need!(r.try_borrow_data()?[11]!=1,8107);let seq={let d=v.try_borrow_data()?;u64at(&d,59)?};v.try_borrow_mut_data()?[67..80].fill(0);
 {let mut d=r.try_borrow_mut_data()?;d[11]=0;d[44..].fill(0);}setguard(g,0)?;let mut event=nonce.to_le_bytes().to_vec();event.extend_from_slice(&seq.to_le_bytes());event.push(0);emit(6,&event);Ok(())
}
fn native_state(t:&AccountInfo,settle:&Pubkey,l:u64)->Res<u64>{
 need!(t.owner==&LEGACY_TOKEN&&t.data_len()==165&&!t.executable,8107);let d=t.try_borrow_data()?;
 need!(d[..32]==WSOL_MINT.to_bytes()&&d[32..64]==settle.to_bytes()&&d[72..76]==[0;4]&&d[108]==1&&d[109..113]==[1,0,0,0]&&u64at(&d,113)?==l&&u64at(&d,121)?==0&&d[129..133]==[0;4],8107);
 let amount=u64at(&d,64)?;need!(add(amount,l)?==t.lamports(),8107);Ok(amount)
}
fn settlement(a:&[AccountInfo],closing:bool,fail:u8)->ProgramResult{
 need!(a.len()==12&&fail<=3,8100);
 let[c,g,v,r,res,temp,settle,payer,token,mint,sys,iv]=a else{return Err(err(8100));};
 controller(c,false)?;states(g,v,r)?;need!(guard(g)?==2,8105);let(current,last,nonce)=tail(iv,false)?;active(v,current,last,nonce)?;
 key(res,&PROOF_RESERVE,true,false)?;need!(zero(res),8101);key(settle,&PROOF_SETTLE_AUTHORITY,false,false)?;need!(zero(settle),8101);
 need!(payer.is_signer&&payer.is_writable&&zero(payer),8101);executable(token,&LEGACY_TOKEN)?;key(mint,&WSOL_MINT,false,false)?;executable(sys,&SYSTEM)?;
 for(i,x)in a.iter().enumerate(){for(j,y)in a[..i].iter().enumerate(){need!(x.key!=y.key||(i==7&&j==0),8103);}}
 let seq=if closing{let d=r.try_borrow_data()?;u64at(&d,44)?}else{let d=v.try_borrow_data()?;sub(u64at(&d,59)?,1)?};let seqbytes=seq.to_le_bytes();
 let (tempkey,bump)=Pubkey::find_program_address(&[b"m4b-proof-wsol",MINT.as_ref(),&seqbytes],&PROOF_PROGRAM);key(temp,&tempkey,true,false)?;let bb=[bump];let tseeds:&[&[u8]]=&[b"m4b-proof-wsol",MINT.as_ref(),&seqbytes,&bb];
 if !closing{
  need!(r.try_borrow_data()?[11]==0&&zero(temp),8107);let p=temp.lamports();let l=Rent::get()?.minimum_balance(165);let d=l.saturating_sub(p);let w=p.saturating_sub(l);let v0=res.lamports();let payer0=payer.lamports();
  add(v0,add(p,d)?)?;need!(payer0>=d,8107);setguard(g,3)?;
  allocate(temp,payer,sys,165,&LEGACY_TOKEN,tseeds)?;
  let mut data=vec![18];data.extend_from_slice(PROOF_SETTLE_AUTHORITY.as_ref());
  invoke(&Instruction{program_id:LEGACY_TOKEN,data,accounts:vec![AccountMeta::new(tempkey,false),AccountMeta::new_readonly(WSOL_MINT,false)]},&[temp.clone(),mint.clone(),token.clone()])?;
  need!(native_state(temp,&PROOF_SETTLE_AUTHORITY,l)?==w&&temp.lamports()==add(p,d)?&&res.lamports()==v0&&payer.lamports()==sub(payer0,d)?,8107);
  {let mut rd=r.try_borrow_mut_data()?;rd[11]=1;for(off,n)in [(44,seq),(52,p),(60,l),(68,d),(76,w),(84,0),(92,v0),(100,payer0)]{put64(&mut rd,off,n);}rd[108..140].copy_from_slice(tempkey.as_ref());rd[140..172].copy_from_slice(payer.key.as_ref());rd[172..204].copy_from_slice(res.key.as_ref());}
  setguard(g,2)?;emit(4,&r.try_borrow_data()?);return Ok(());
 }
 let(p,l,d,w,v0,payer0)={let rd=r.try_borrow_data()?;need!(rd[11]==1&&rd[108..140]==tempkey.to_bytes()&&rd[140..172]==payer.key.to_bytes()&&rd[172..204]==PROOF_RESERVE.to_bytes(),8107);(u64at(&rd,52)?,u64at(&rd,60)?,u64at(&rd,68)?,u64at(&rd,76)?,u64at(&rd,92)?,u64at(&rd,100)?)};
 need!(l==Rent::get()?.minimum_balance(165)&&d==l.saturating_sub(p)&&w==p.saturating_sub(l)&&res.lamports()==v0&&payer.lamports()==sub(payer0,d)?,8107);
 let amount=native_state(temp,&PROOF_SETTLE_AUTHORITY,l)?;let output=sub(amount,w)?;let total=add(add(p,d)?,output)?;need!(temp.lamports()==total,8107);let closed_reserve=add(v0,total)?;
 setguard(g,3)?;let sb=[pda(b"m4b-proof-settle").1];
 invoke_signed(&Instruction{program_id:LEGACY_TOKEN,data:vec![9],accounts:vec![AccountMeta::new(tempkey,false),AccountMeta::new(PROOF_RESERVE,false),AccountMeta::new_readonly(PROOF_SETTLE_AUTHORITY,true)]},&[temp.clone(),res.clone(),settle.clone(),token.clone()],&[&[b"m4b-proof-settle",MINT.as_ref(),&sb]])?;
 // This observation occurs in SBF immediately after captured native CPI, before any restoration.
 let observed_owner=*temp.owner;let observed_len=temp.data_len() as u64;let observed_lamports=temp.lamports();
 solana_program::msg!("M4B actual postclose owner={} data_len={} lamports={}",observed_owner,observed_len,observed_lamports);
 need!(zero(temp)&&observed_lamports==0&&res.lamports()==closed_reserve,8107);
 if fail==1{return Err(err(8108));}let rb=[pda(b"m4b-proof-reserve").1];let rseeds:&[&[u8]]=&[b"m4b-proof-reserve",MINT.as_ref(),&rb];
 native_transfer(res,payer,sys,d,Some(rseeds))?;need!(payer.lamports()==payer0&&res.lamports()==sub(closed_reserve,d)?,8107);if fail==2{return Err(err(8108));}
 native_transfer(res,temp,sys,p,Some(rseeds))?;need!(zero(temp)&&temp.lamports()==p&&res.lamports()==add(v0,output)?,8107);if fail==3{return Err(err(8108));}
 {let mut rd=r.try_borrow_mut_data()?;rd[11]=2;put64(&mut rd,84,output);}setguard(g,2)?;
 let mut event=r.try_borrow_data()?.to_vec();event.extend_from_slice(observed_owner.as_ref());event.extend_from_slice(&observed_len.to_le_bytes());event.extend_from_slice(&observed_lamports.to_le_bytes());event.extend_from_slice(&closed_reserve.to_le_bytes());emit(5,&event);Ok(())
}
entrypoint!(process_instruction);
pub fn process_instruction(id:&Pubkey,a:&[AccountInfo],data:&[u8])->ProgramResult{
 need!(id==&PROOF_PROGRAM,8101);need!(data.len()>=9&&&data[..8]==b"M4BPRF01",8100);let tag=data[8];
 match tag{0=>{need!(data.len()==9,8100);bootstrap(a)},1|7=>{need!(data.len()==10,8100);probe(a,tag,data[9])},2|3|8=>{need!(data.len()==9,8100);probe(a,tag,0)},4=>{need!(data.len()==9,8100);settlement(a,false,0)},5=>{need!(data.len()==10,8100);settlement(a,true,data[9])},6=>{need!(data.len()==17,8100);finalizer(a,u64at(data,9)?)},_=>Err(err(8100))}
}
