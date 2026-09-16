# Literary gate sidecars

Contracts: `contracts/authorial_voice.py`. Executor: `authorial_voice.evaluate_intervention`.
CLI input is `{gate, candidate?, budget?}`. Missing literary intent, insufficient
investment or arc, sufficient visual expression and unexplained repeated gestures
all suppress text. Historical weight contributes reasons; it is not a numerical
override for an unearned scene. Do not equate main role with QUALIFIED.

Store source pins and findings with reasons; LiteraryCodaEligibility is the reasoned
assessment, not the ultimate instruction to speak. For a no-text visual coda, give
semantic purpose only and hand it to downstream direction. This executor reports
NO_AUTHORIAL_INTERVENTION because no authorial words are requested.

For REDUNDANCY_SCARCITY and OVER_EXPLANATION_RISK, QUALIFIED means a reasoned
clearance to intervene (sufficient scarcity / acceptably low explanation risk).
PARTIAL or NOT_QUALIFIED suppresses text. VISUAL_SUFFICIENCY instead assesses whether
the image itself is sufficient; the explicit visualSufficient flag enforces silence.
Record both dimension reasons and the actual intervention ledger, not one or the other.

AuthorialVoiceBudget has recentInterventions (source-pinned actual uses),
distinctContributionAgainst (a reason for each previous use) and
repetitionExplanations (a reason for each repeated form/motif/emotion). Reviewing more
uses therefore raises the burden of justification without fixing any number limit.
Do not fabricate a clean ledger when earlier episodes have not been checked.

Text provenance has a closed factual relation, but literary form is an open string.
Every new form needs a rationale. Historical excerpts must be verified by the Host;
the executor checks equality and explicit source pins, not external authenticity.
Original/adapted statements are interpretations; no automatic canonical promotion.

Review literary benefit against redundancy, attention stolen from the last action,
false certainty and forced solemnity. A text option can be retained for comparison
even if the gate recommends silence; do not reinterpret retention as eligibility.

Scarcity also considers characterIds on candidates/prior uses and nearbyInterventionKeys
on the budget. Mark proximity from the actual dramatic sequence, not a fixed seconds
quota. Same-character or nearby reuse requires its own contextual justification even
when form, motif and emotional function differ. Dry-run stress fixtures must be labeled
as hypothetical, never entered as adopted uses.
