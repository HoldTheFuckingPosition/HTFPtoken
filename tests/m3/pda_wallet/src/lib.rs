//! Authenticated artificial caller fixture only. Never a product wallet.
use solana_program::{account_info::AccountInfo,entrypoint,entrypoint::ProgramResult,
 instruction::{AccountMeta,Instruction},program::invoke_signed,program_error::ProgramError,pubkey::Pubkey};
const HELPER:Pubkey=Pubkey::new_from_array([7, 137, 46, 4, 193, 185, 37, 95, 147, 103, 193, 249, 179, 152, 165, 231, 94, 212, 57, 117, 144, 68, 45, 89, 107, 71, 165, 164, 44, 202, 238, 60]);
const H:Pubkey=solana_program::pubkey!("CseQKCWvi4EA2o3oa11Age4p4xKWSLuzjWCzitASrPJu");
const CONTROLLER:Pubkey=solana_program::pubkey!("Hyx62wPQGyvXCoihZq1BrbUjBRh2LuNxWiiqMkfAuSZr");
entrypoint!(process);
pub fn process(id:&Pubkey,a:&[AccountInfo],data:&[u8])->ProgramResult{
 if id!=&HELPER || a.len()!=11 || data.len()!=56 || &data[..6]!=b"HTFP\x01\x02" || data[54..]!=[0,0] {
  return Err(ProgramError::Custom(9000));
 }
 if a[0].key!=&CONTROLLER || !a[0].is_signer {return Err(ProgramError::Custom(9001));}
 if a[1].key!=&H || !a[1].executable {return Err(ProgramError::Custom(9002));}
 let (wallet,bump)=Pubkey::find_program_address(&[b"wallet-holder"],id);
 if a[8].key!=&wallet {return Err(ProgramError::Custom(9003));}
 // Controller's actual transaction signature binds original amount/minimum/payee bytes/metas.
 // Forward exactly those bytes/metas to pinned H; elevate only this canonical wallet PDA.
 let metas=a[2..].iter().enumerate().map(|(j,x)|AccountMeta{
  pubkey:*x.key,is_writable:x.is_writable,is_signer:if j==6{true}else{x.is_signer}
 }).collect();
 let ix=Instruction{program_id:H,accounts:metas,data:data.to_vec()};
 let mut infos=a[2..].to_vec();infos.push(a[1].clone());
 let bb=[bump];
 invoke_signed(&ix,&infos,&[&[b"wallet-holder",&bb]])?;
 Ok(())
}
