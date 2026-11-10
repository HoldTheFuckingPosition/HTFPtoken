#![allow(unexpected_cfgs,deprecated)]
mod constants;
use constants::*;
use solana_program::{account_info::AccountInfo,entrypoint,entrypoint::ProgramResult,program_error::ProgramError,
 instruction::{AccountMeta,Instruction,get_stack_height},program::invoke,pubkey::Pubkey};
fn error(n:u32)->ProgramError{ProgramError::Custom(n)}
entrypoint!(process_instruction);
pub fn process_instruction(id:&Pubkey,a:&[AccountInfo],d:&[u8])->ProgramResult{
 if id!=&WALLET_PROGRAM||d.len()!=17||&d[..8]!=b"M4BWAL01"||d[8]>8||a.len()!=9{return Err(error(8100));}
 let keys=[INITIALIZER,PROOF_GUARD,PROOF_VOLUME,PROOF_RECORD,PROOF_MARKER,INSTRUCTIONS_SYSVAR,SYSTEM,PROOF_PROGRAM,WALLET_PROGRAM];
 for(i,k)in keys.iter().enumerate(){if a[i].key!=k{return Err(error(8101));}}
 if !a[0].is_signer||!a[0].is_writable||a[0].owner!=&SYSTEM||a[0].data_len()!=0||a[0].executable||a[5].is_writable||!a[7].executable||!a[8].executable{return Err(error(8101));}
 for x in &a[1..5]{if !x.is_writable{return Err(error(8101));}}
 let height=get_stack_height();if height>3||d[8]==4&&height>1{return Err(error(8106));}
 let base=vec![AccountMeta::new(INITIALIZER,true),AccountMeta::new(PROOF_GUARD,false),AccountMeta::new(PROOF_VOLUME,false),AccountMeta::new(PROOF_RECORD,false),AccountMeta::new(PROOF_MARKER,false),AccountMeta::new_readonly(INSTRUCTIONS_SYSVAR,false),AccountMeta::new_readonly(SYSTEM,false)];
 let run=|tag:u8,payload:Option<u8>|->ProgramResult{let mut data=b"M4BPRF01".to_vec();data.push(tag);if let Some(x)=payload{data.push(x);}invoke(&Instruction{program_id:PROOF_PROGRAM,accounts:base.clone(),data},a)};
 let finish=||->ProgramResult{let mut data=b"M4BPRF01".to_vec();data.push(6);data.extend_from_slice(&d[9..17]);let accounts=vec![AccountMeta::new_readonly(INITIALIZER,true),AccountMeta::new(PROOF_GUARD,false),AccountMeta::new(PROOF_VOLUME,false),AccountMeta::new(PROOF_RECORD,false),AccountMeta::new_readonly(INSTRUCTIONS_SYSVAR,false)];invoke(&Instruction{program_id:PROOF_PROGRAM,accounts,data},a)};
 match d[8]{0=>run(1,Some(0)),1=>{run(1,Some(0))?;let r=run(2,None);solana_program::msg!("M4B attempted ignore Recover child result {:?}",r);Ok(())},2=>{run(1,Some(0))?;let r=finish();solana_program::msg!("M4B attempted ignore Finalize child result {:?}",r);Ok(())},3=>{run(1,Some(0))?;run(8,None)},4=>{let mut data=d.to_vec();data[8]=0;let mut accounts=base;accounts.push(AccountMeta::new_readonly(PROOF_PROGRAM,false));accounts.push(AccountMeta::new_readonly(WALLET_PROGRAM,false));invoke(&Instruction{program_id:WALLET_PROGRAM,accounts,data},a)},5=>finish(),6=>Ok(()),7=>{let r=run(1,Some(1));solana_program::msg!("M4B attempted ignore failed Probe child result {:?}",r);Ok(())},8=>run(2,None),_=>Err(error(8100))}
}
