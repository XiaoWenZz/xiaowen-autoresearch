# Editable Research Map Maintenance

Use an editable, draggable research map as a compact navigation and decision
surface. Never use it as the source of scientific evidence.

Use the workspace's declared standard format. When none is declared, prefer a
standard `.xmind` file over browser-only HTML so a person can drag, fold, edit,
and save the map in a normal mind-mapping application. Keep generated previews
derived and disposable.

## Contents

- [Source order](#source-order)
- [Trigger the update](#trigger-the-update)
- [Preserve identity and scope](#preserve-identity-and-scope)
- [Keep the node contract small](#keep-the-node-contract-small)
- [Maintain the editable artifact](#maintain-the-editable-artifact)
- [Validate before handoff](#validate-before-handoff)

## Source order

Resolve conflicts in this order:

1. Preserve raw artifacts, run manifests, and frozen outcome records.
2. Update the linked Wiki or project knowledge page from those records.
3. Update the research map from the resulting scoped decision.

Keep the map disposable and reconstructable from authoritative records. Do not
edit an experiment outcome to make the map look consistent.

## Trigger the update

Update the affected branch at these milestones only:

- charter freeze or material amendment;
- independently verified outcome;
- Opportunity, Scout, or contribution promotion;
- scoped stop, carrier-level stop, or formal reduction;
- structural pivot or Program/Epoch archive;
- explicit rolling-window refresh, such as a two-week idea review.

Do not update for heartbeats, queue changes, ordinary engineering retries,
intermediate metrics, presentation-only wording, or a failed run that emitted
no estimand and changed no scientific status.

## Preserve identity and scope

- Assign one stable node ID to one causal fingerprint, Program/Epoch, or route.
- Preserve that ID across renames, carrier swaps, parameter changes, and label
  cleanup when the distinct prediction is unchanged.
- Create a new node only for a genuinely new problem thesis, causal mechanism,
  or prospectively frozen discriminator.
- Move a node to a new parent only after a real problem or Program reframe.
- Update the smallest affected branch. Do not rewrite unrelated history.
- Never delete a negative result merely because it leaves a rolling window.
  Archive or filter it while retaining the authoritative record.

## Keep the node contract small

Preserve only semantics the editable artifact can round-trip:

- stable topic ID and exactly one root;
- parent-child hierarchy;
- plain-language title;
- presentation status, not the scientific terminal code;
- note text in the form
  `attempt -> evidence -> blocker -> claim boundary/reopen condition`;
- optional side, fold, and manual layout state; never interpret layout as
  evidence.

When the map uses the compact `R/C/E/T/H` legend, apply it conservatively:

- `R`: valid empirical evidence supports a scoped route stop;
- `C`: carrier, identifiability, or evidence-contract block;
- `E`: engineering-invalid run; no scientific result;
- `T`: theory or preserving-reduction result;
- `H`: held, challenged, observed, or not yet promoted.

Keep the exact scientific state and terminal code in the linked record. Never
turn `E`, `C`, `H`, or search exhaustion into `R` or a broad NO-GO for visual
simplicity.

## Maintain the editable artifact

1. Read the affected experiment outcomes and linked Wiki state.
2. Copy the current editable map before editing when an update may be lossy.
3. Modify only affected nodes; preserve IDs and intentional manual layout.
4. Save the standard editable artifact to the path named by `AGENTS.md`, the
   charter, or the existing knowledge workflow. For XMind, keep `.xmind` as the
   primary artifact; its packaged `content.json` is sufficient unless the
   workspace explicitly requires a separate JSON sidecar.
5. Reopen the saved artifact and check titles, notes, branches, folding,
   dragging, and status legend.
6. Record `map_sync=complete`, `map_sync=pending`, or `map_sync=not_configured`
   in the ordinary handoff note; do not create a parallel state system.

If no persistent map destination is defined, do not invent a workspace
dependency. Report `map_sync=not_configured`; offer the editable artifact and
portable source data as a handoff deliverable. If the destination is dirty or
unavailable, preserve the new artifact separately and report
`map_sync=pending`.

## Validate before handoff

Check that the artifact parses, IDs are unique, exactly one root exists, every
parent exists, and no parent cycle exists. For `.xmind`, verify the ZIP package
contains valid `content.json`, `metadata.json`, and `manifest.json`, then reopen
it in XMind or a compatible reader when available. Compare each changed node
with the authoritative record and verify:

- the blocker type and claim boundary match;
- engineering-invalid work is not shown as a scientific negative;
- a scoped stop is not expanded into a Program or field-level closure;
- held or challenged work retains its reopening condition;
- rolling-window coverage includes every in-scope idea without silently
  merging distinct predictions or duplicating renamed versions.

Treat a map rendering or sync defect as knowledge-maintenance work. It blocks
scientific closure only when the workspace explicitly declares the map a
required completion artifact.
