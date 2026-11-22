//! Permanent reserve funding for the fresh production-volume profile.
//! The zero-data reserve retains its original address and all direct SOL receipts.

use super::*;

const SEED: &[u8] = b"htfp-reserve-storage";
const HEADER: &[u8; 8] = b"HTFPRNT1";
const SIZE: usize = 17;
const INVALID_RECORD: u32 = 7027;
const TECHNICAL_TOP_UP_REQUIRED: u32 = 7028;
const TECHNICAL_BALANCE_DEFICIT: u32 = 7029;
const INVALID_TOP_UP_QUOTE: u32 = 7030;
const INSUFFICIENT_SPONSOR_FUNDS: u32 = 7031;

fn storage_address() -> (Pubkey, u8) {
    Pubkey::find_program_address(&[SEED, MINT.as_ref()], &PROGRAM)
}

pub(super) fn read(record: &AccountInfo<'_>) -> Res<u64> {
    let (address, bump) = storage_address();
    check!(record.key == &address && record.owner == &PROGRAM && !record.executable, INVALID_RECORD);
    let bytes = record.try_borrow_data()?;
    check!(bytes.len() == SIZE && &bytes[..8] == HEADER && bytes[8] == bump, INVALID_RECORD);
    u64_at(&bytes, 9)
}

pub(super) fn backing(balance: u64, technical: u64, live_rent: u64) -> Res<u64> {
    let value = balance.checked_sub(technical).ok_or(fail(TECHNICAL_BALANCE_DEFICIT))?;
    check!(live_rent <= technical, TECHNICAL_TOP_UP_REQUIRED);
    Ok(value)
}

pub(super) fn top_up(accounts: &[AccountInfo<'_>], data: &[u8]) -> ProgramResult {
    check!(data.len() == 22, 7000);
    let [payer, reserve, record, system] = accounts else { return Err(fail(7000)); };
    unique(accounts)?;
    required(payer, true, true)?;
    required(reserve, true, false)?;
    required(record, true, false)?;
    identity(reserve, &RESERVE)?;
    program(system, &SYSTEM)?;
    check!(system_zero(payer) && !protected(payer) && system_zero(reserve), 7001);

    let technical = read(record)?;
    let reserve_before = reserve.lamports();
    let economic = reserve_before.checked_sub(technical).ok_or(fail(TECHNICAL_BALANCE_DEFICIT))?;
    let live_rent = Rent::get()?.minimum_balance(0);
    let amount = live_rent.checked_sub(technical).filter(|amount| *amount > 0)
        .ok_or(fail(INVALID_TOP_UP_QUOTE))?;
    check!(u64_at(data, 6)? == technical && u64_at(data, 14)? == amount, INVALID_TOP_UP_QUOTE);
    let payer_after = payer.lamports().checked_sub(amount).ok_or(fail(INSUFFICIENT_SPONSOR_FUNDS))?;
    let reserve_after = checked_add(reserve_before, amount)?;

    invoke(&system_instruction::transfer(payer.key, reserve.key, amount),
        &[payer.clone(), reserve.clone(), system.clone()])?;
    check!(payer.lamports() == payer_after && reserve.lamports() == reserve_after
        && system_zero(payer) && system_zero(reserve), 7013);
    record.try_borrow_mut_data()?[9..17].copy_from_slice(&live_rent.to_le_bytes());
    check!(read(record)? == live_rent && backing(reserve.lamports(), live_rent, live_rent)? == economic, 7013);
    Ok(())
}

pub(super) struct Funding {
    bump: u8,
    record_shortfall: u64,
    technical: u64,
}

impl Funding {
    pub(super) fn prepare(record: &AccountInfo<'_>, reserve: &AccountInfo<'_>, rent: &Rent) -> Res<Self> {
        let (address, bump) = storage_address();
        check!(record.key == &address && system_zero(record), INVALID_RECORD);
        required(record, true, false)?;
        required(reserve, true, false)?;
        Ok(Self {
            bump,
            record_shortfall: rent.minimum_balance(SIZE).saturating_sub(record.lamports()),
            technical: rent.minimum_balance(0),
        })
    }

    pub(super) fn payer_cost(&self) -> Res<u64> {
        checked_add(self.record_shortfall, self.technical)
    }

    pub(super) fn technical_lamports(&self) -> u64 {
        self.technical
    }

    pub(super) fn fund<'info>(&self, record: &AccountInfo<'info>, reserve: &AccountInfo<'info>,
        payer: &AccountInfo<'info>, system: &AccountInfo<'info>) -> ProgramResult {
        let payer_before = payer.lamports();
        let reserve_before = reserve.lamports();
        let record_before = record.lamports();
        bootstrap(record, payer, system, SIZE, &PROGRAM, SEED, self.bump)?;
        if self.technical != 0 {
            invoke(&system_instruction::transfer(payer.key, reserve.key, self.technical),
                &[payer.clone(), reserve.clone(), system.clone()])?;
        }
        check!(payer_before.checked_sub(payer.lamports()) == Some(self.payer_cost()?)
            && reserve.lamports().checked_sub(reserve_before) == Some(self.technical)
            && record.lamports().checked_sub(record_before) == Some(self.record_shortfall)
            && system_zero(reserve), 7013);
        {
            let mut bytes = record.try_borrow_mut_data()?;
            bytes[..8].copy_from_slice(HEADER);
            bytes[8] = self.bump;
            bytes[9..].copy_from_slice(&self.technical.to_le_bytes());
        }
        check!(read(record)? == self.technical, 7013);
        Ok(())
    }
}
