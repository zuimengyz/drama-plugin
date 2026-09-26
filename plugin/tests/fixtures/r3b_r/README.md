# Frozen R3C regression inputs

Byte-for-byte copies of the NOT_ADOPTED R3C sidecar and Director candidate from
`artifacts/flagship-literary-film-01/creative/screenplay-r3`, captured during
R3B-R at baseline HEAD `df625f9d01cc62c3f1ffed2774e88166ab37bae5`.

These are read-only test inputs, not a new creative revision or approval.
Mutation tests alter in-memory copies only. The candidate recheck deliberately
keeps the old S03 Director receipt pin and asserts staleness against the corrected
receipt; it never silently rewrites creative or projection fingerprints.

SHA256:

- Sidecar: `90ceeda49fee4542c1cb08b482bc9deb23fc6d4945690fdaddd26c876356a1a6`
- Director: `4f1033e73234c5ae5dddbbb630694502e24250f4f9e4d1798c2debe6c94187ef`
