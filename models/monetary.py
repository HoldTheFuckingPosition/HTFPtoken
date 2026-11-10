"""M1 exact-integer reference model only; not an HTFP on-chain implementation.

D01/D02/D19/D20/D23/D25/D26; F01-F04/F07/F13-F15/F21-F26;
SEC01-SEC05/SEC07-SEC10. Authority, signing, CPI, payout failure and AMM
execution are deliberately outside this mathematical model.
"""
from dataclasses import dataclass, replace

U64_MAX = (1 << 64) - 1
U128_MAX = (1 << 128) - 1
DECIMALS = 7
INITIAL_SUPPLY = 10**12 * 10**DECIMALS
BPS_DENOMINATOR = 10_000


class DomainError(ValueError):
    """An exact input, bound or monetary precondition is violated."""


def uint(value: int, maximum: int = U64_MAX) -> int:
    """Reject bool, float, strings and out-of-domain values without coercion."""
    if type(value) is not int or not 0 <= value <= maximum:
        raise DomainError("expected exact unsigned integer within bound")
    return value


def checked_product(a: int, b: int) -> int:
    a, b = uint(a, U128_MAX), uint(b, U128_MAX)
    product = a * b
    if product > U128_MAX:
        raise DomainError("u128 product overflow")
    return product


def encode_u64(value: int) -> bytes:
    return uint(value).to_bytes(8, "little")


def decode_u64(data: bytes) -> int:
    if type(data) is not bytes or len(data) != 8:
        raise DomainError("expected exactly eight bytes")
    return int.from_bytes(data, "little")


def transfer_fee(amount: int, bps: int, maximum_fee: int = U64_MAX) -> int:
    amount, bps, maximum_fee = uint(amount), uint(bps, BPS_DENOMINATOR), uint(maximum_fee)
    quotient, remainder = divmod(checked_product(amount, bps), BPS_DENOMINATOR)
    return min(maximum_fee, quotient + (remainder != 0))


def round_inventory(recovered: int) -> tuple[int, int]:
    """Arithmetic bound only; volume limits may leave a much larger backlog."""
    recovered = uint(recovered)
    return recovered - recovered % 8, recovered % 8


def allocate(q: int) -> tuple[int, int]:
    q = uint(q)
    if not q or q % 8:
        raise DomainError("processing Q must be a positive multiple of eight")
    return 3 * (q // 8), 5 * (q // 8)


def sale_accounting(q: int, bps: int = 800) -> tuple[int, int, int, int]:
    """One-pass bookkeeping only: withheld sale fee is future inventory."""
    burn, gross = allocate(q)
    withheld = transfer_fee(gross, bps)
    return burn, gross, withheld, gross - withheld


@dataclass(frozen=True)
class RedemptionState:
    """Actual native supply and total reserve; maintenance is an explicit input.

    holder_balance is only the requesting holder's spendable tokens. Supply
    includes other wallets, pool/custody and withheld units until native burn.
    No function here mints, sweeps, authenticates signers or executes payments.
    """
    supply: int
    reserve: int
    maintenance: int
    holder_balance: int

    def __post_init__(self):
        for value in (self.supply, self.reserve, self.maintenance, self.holder_balance):
            uint(value)
        if self.reserve < self.maintenance or self.holder_balance > self.supply:
            raise DomainError("inconsistent reserve or supply state")

    @property
    def spendable(self) -> int:
        return self.reserve - self.maintenance


def quote(state: RedemptionState, amount: int, minimum: int = 0) -> int:
    """Pre-burn quote; minimum represents a bound supplied by an authorized user."""
    amount, minimum = uint(amount), uint(minimum)
    if state.supply == 0 or not 0 < amount <= state.holder_balance:
        raise DomainError("zero supply, invalid amount or insufficient holder balance")
    payout = checked_product(state.spendable, amount) // state.supply
    if payout == 0 or payout < minimum:
        raise DomainError("zero output or minimum not met")
    return payout


def redeem(state: RedemptionState, amount: int, minimum: int = 0) -> tuple[RedemptionState, int]:
    """Immutable mathematical state transition, not runtime payout rollback proof."""
    payout = quote(state, amount, minimum)
    return replace(state, supply=state.supply - amount,
                   reserve=state.reserve - payout,
                   holder_balance=state.holder_balance - amount), payout


def external_burn(state: RedemptionState, amount: int) -> RedemptionState:
    amount = uint(amount)
    if not 0 < amount <= state.holder_balance:
        raise DomainError("invalid external holder burn")
    return replace(state, supply=state.supply - amount,
                   holder_balance=state.holder_balance - amount)


def native_donation(state: RedemptionState, lamports: int) -> RedemptionState:
    """Later SOL remains physically present even at zero supply; no sweep path."""
    reserve = uint(state.reserve + uint(lamports))
    return replace(state, reserve=reserve)
