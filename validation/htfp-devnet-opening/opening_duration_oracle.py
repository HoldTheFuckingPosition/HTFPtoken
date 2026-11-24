"""Offline reference arithmetic for the three inspected Alpenglow source paths."""
from dataclasses import dataclass


NANOS_PER_SECOND = 1_000_000_000
I64_MAX = 2**63 - 1
U64_MAX = 2**64 - 1
DELAY_EPOCHS = 2


@dataclass(frozen=True)
class Geometry:
    slots_per_epoch: int
    initial_slot: int
    initial_epoch: int

    def epoch(self, slot):
        if not 0 <= self.initial_epoch <= U64_MAX or not 0 <= self.initial_slot <= slot <= U64_MAX:
            raise ValueError('Slot outside the declared normal geometry')
        if not 32 <= self.slots_per_epoch <= U64_MAX:
            raise ValueError('Invalid normal epoch length')
        epoch = self.initial_epoch + (slot - self.initial_slot) // self.slots_per_epoch
        if epoch > U64_MAX:
            raise ValueError('Slot epoch overflows')
        return epoch

    def first_slot(self, epoch):
        self.epoch(self.initial_slot)
        if epoch < self.initial_epoch:
            raise ValueError('Epoch predates the normal geometry')
        slot = self.initial_slot + (epoch - self.initial_epoch) * self.slots_per_epoch
        if slot > U64_MAX:
            raise ValueError('Epoch slot overflows')
        return slot


def effective_slot_changes(geometry, baseline_ns, gates):
    """Translate observed feature activation slots into nonincreasing slot durations."""
    if not 0 < baseline_ns <= U64_MAX:
        raise ValueError('Invalid nominal duration')
    duration = baseline_ns
    active = [(geometry.first_slot(geometry.epoch(slot) + 1), nanos) for slot, nanos in gates]
    transitions = [(0, duration)]
    for slot, nanos in sorted(active):
        if not 0 < nanos <= U64_MAX:
            raise ValueError('Invalid gated duration')
        if nanos < duration:
            duration = nanos
            if transitions[-1][0] == slot:
                transitions.pop()
            transitions.append((slot, duration))
    return transitions


def elapsed_duration_half_open(begin, end, transitions):
    """Sum nominal duration over slots [begin, end), including skipped slots."""
    if not 0 <= begin <= end <= U64_MAX:
        raise ValueError('Invalid half-open slot interval')
    duration = transitions[0][1]
    after_begin = []
    for slot, nanos in transitions:
        if slot <= begin:
            duration = nanos
        elif slot < end:
            after_begin.append((slot, nanos))
    total = 0
    cursor = begin
    for slot, next_duration in after_begin:
        total += (slot - cursor) * duration
        cursor, duration = slot, next_duration
    return total + (end - cursor) * duration


def elapsed_duration_inclusive(parent, child, transitions):
    """Agave's inclusive parent+1 ..= child agrees with Firedancer's half-open range."""
    if parent > child or child == U64_MAX:
        raise ValueError('Invalid parent and child slot pair')
    return elapsed_duration_half_open(parent + 1, child + 1, transitions)


def conditional_arithmetic(geometry, earliest_post_migration, anchor_slot, nanoseconds, scheduling_epoch,
                           baseline_ns, observed_gates):
    """Return a conditional mathematical result without authenticating any inputs."""
    if not 0 <= earliest_post_migration < anchor_slot:
        raise ValueError('Anchor must be strictly after the migration bank')
    if not 0 < nanoseconds <= I64_MAX:
        raise ValueError('Invalid signed footer nanoseconds')
    activation_slot = geometry.first_slot(scheduling_epoch + DELAY_EPOCHS)
    anchor_epoch = geometry.epoch(anchor_slot)
    if not scheduling_epoch <= anchor_epoch < scheduling_epoch + DELAY_EPOCHS:
        raise ValueError('Anchor must be after scheduling and before activation')
    last = activation_slot - 1
    if anchor_slot >= last:
        raise ValueError('No future pre-activation slot remains')
    transitions = effective_slot_changes(geometry, baseline_ns, observed_gates)
    elapsed = elapsed_duration_inclusive(anchor_slot, last, transitions)
    # Both signed-i64 implementations clamp the increment and then their sum.
    upper_ns = min(I64_MAX, nanoseconds + min(I64_MAX, 2 * elapsed))
    upper_seconds = upper_ns // NANOS_PER_SECOND
    if upper_seconds == I64_MAX // NANOS_PER_SECOND:
        raise ValueError('No finite admitted opening in the signed-nanosecond domain')
    return dict(status='CONDITIONAL_ARITHMETIC_ONLY', activation_slot=activation_slot,
                last_pre_activation_slot=last, inclusive_maximum_seconds=upper_seconds,
                minimum_conditional_opening_seconds=upper_seconds + 1)
