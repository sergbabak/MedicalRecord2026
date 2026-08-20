# Medical Record 2026 RC 0.4.1 source payload

The RC 0.4.1 source tree is stored in `rc041.part00` … `rc041.part17` as contiguous Base64 chunks of a single XZ-compressed tar archive. Native CI concatenates the chunks in lexical order, decodes the archive, verifies SHA-256 `d177b4bc89a7bf01ca7ef04dc42459472fe0164797a10088255cbcc0b5cecd00`, and only then extracts/builds it.

This staging representation is used to preserve the exact source archive transferred into GitHub before the first native Windows/macOS validation run.
