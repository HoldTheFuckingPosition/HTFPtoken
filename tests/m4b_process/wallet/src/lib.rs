#![allow(deprecated,unexpected_cfgs)]
mod constants;
use constants::*;
use solana_program::{account_info::AccountInfo,entrypoint,entrypoint::ProgramResult,program_error::ProgramError,pubkey::Pubkey,instruction::{Instruction,AccountMeta,get_stack_height},program::invoke};
fn err(n:u32)->ProgramError{ProgramError::Custom(n)}
entrypoint!(process_instruction);
pub fn process_instruction(id:&Pubkey,a:&[AccountInfo],d:&[u8])->ProgramResult{
 if !cfg!(feature="local-wallet")||id!=&WALLET||d.len()!=25||&d[..8]!=b"HTFPM4W1"||d[8]>10||a.len()!=25{return Err(err(8200));}
 let expected=[CONFIG,INVENTORY,VOLUME,MINT,CUSTODY,TAX_AUTHORITY,RESERVE,*a[7].key,SETTLE_AUTHORITY,*a[9].key,TOKEN2022,LEGACY_TOKEN,WSOL_MINT,SYSTEM,INSTRUCTIONS_SYSVAR,AMM,AMM_CONFIG,AMM_AUTHORITY,POOL,VAULT_HTFP,VAULT_WSOL,OBSERVATION,INITIALIZER,PROGRAM,WALLET];
 for(i,k)in expected.iter().enumerate(){if a[i].key!=k{return Err(err(8201));}}
 if !a[22].is_signer||a[22].owner!=&SYSTEM||a[22].data_len()!=0||a[22].executable||!a[23].executable||!a[24].executable||!a[9].is_signer||a[9].owner!=&SYSTEM||a[9].data_len()!=0{return Err(err(8201));}
 if get_stack_height()>2||d[8]==4&&get_stack_height()!=1{return Err(err(8202));}
 let q=&d[9..17];let nonce=&d[17..25];
 if d[8]==10&&q!=[0u8;8]{return Err(err(8200));}
 let process=||->ProgramResult{let mut data=b"HTFP\x01\x03".to_vec();data.extend_from_slice(q);let writable=[1usize,2,3,4,6,7,9,18,19,20,21];let accounts=a[..22].iter().enumerate().map(|(i,x)|if writable.contains(&i){AccountMeta::new(*x.key,i==9)}else{AccountMeta::new_readonly(*x.key,false)}).collect();invoke(&Instruction{program_id:PROGRAM,accounts,data},a)};
 let recover=|with_vault:bool|->ProgramResult{let mut data=b"HTFP\x01\x01".to_vec();data.extend_from_slice(&(if with_vault{1u16}else{0u16}).to_le_bytes());let mut accounts=vec![AccountMeta::new_readonly(CONFIG,false),AccountMeta::new(INVENTORY,false),AccountMeta::new(MINT,false),AccountMeta::new(CUSTODY,false),AccountMeta::new_readonly(TAX_AUTHORITY,false),AccountMeta::new_readonly(TOKEN2022,false)];if with_vault{accounts.push(AccountMeta::new(VAULT_HTFP,false));}invoke(&Instruction{program_id:PROGRAM,accounts,data},a)};
 let finish=||->ProgramResult{let mut data=b"HTFP\x01\x05".to_vec();data.extend_from_slice(nonce);let accounts=vec![AccountMeta::new_readonly(CONFIG,false),AccountMeta::new(INVENTORY,false),AccountMeta::new(VOLUME,false),AccountMeta::new_readonly(INSTRUCTIONS_SYSVAR,false)];invoke(&Instruction{program_id:PROGRAM,accounts,data},a)};
 match d[8]{0=>process(),1=>{process()?;recover(true)},2=>recover(true),3=>finish(),4=>{let mut data=d.to_vec();data[8]=0;let accounts=a.iter().map(|x|if x.is_writable{AccountMeta::new(*x.key,x.is_signer)}else{AccountMeta::new_readonly(*x.key,x.is_signer)}).collect();invoke(&Instruction{program_id:WALLET,accounts,data},a)},5=>{process()?;let r=recover(true);solana_program::msg!("H wallet attempted ignore child error {:?}",r);Ok(())},6=>Ok(()),7=>recover(false),8=>{process()?;recover(false)},9=>{process()?;finish()},10=>{let r=process();solana_program::msg!("H wallet attempted ignore initially failed Process {:?}",r);Ok(())},_=>Err(err(8200))}
}
