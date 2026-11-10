# Native DOM control identity

## NCI1 · exploratory · 2026-11-10 18:52
Question: do the exact owned More options controls expose a closest direct AXWebArea ancestor with actual HTTP(S) AXURL suitable for a scoped DOM identifier?
Test: one fresh bound-window SDK observation, independently resolve the two exact named controls by role/frame and walk at most32 direct AXParent links each, recording only role, exact control name/DOM ID and closest WebArea URL; no input or focus writes. SDK WebArea resolution may be recorded separately without inferring direct containment.
Refs: output/suno-20261110/SUN25-hero-peer-probe.json
