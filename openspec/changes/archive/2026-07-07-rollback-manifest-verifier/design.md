# Design

The verifier keeps the profile as the binding manifest and treats rollback
window evidence as the trust carrier. The profile names the manifest and lists
completed scenarios; the manifest must independently prove the same scenario set.

Validation is deliberately generic:

1. Resolve the manifest path under the adopter repository and reject absolute or
   escaping paths.
2. Require the manifest file and every scenario evidence file to be Git-tracked.
3. Parse the manifest as TOML.
4. Require `target_head` and `product_head` to name commits reachable from the
   current adopter and external-product repositories.
5. Require every standard scenario (`proof_report`, `work_lane_closeout`,
   `domain_gate`, `assistant_playbook`) plus adopter-added required scenarios to
   include matching target/product heads, a command, an evidence path, and a
   digest.

This prevents a placeholder file or profile-only declaration from making a
terminal `retirement_ready` backend state pass.
