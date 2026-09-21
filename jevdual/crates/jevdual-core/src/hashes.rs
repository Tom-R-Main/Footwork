//! R3: batched element hashes (port of `EnhancedDOMTreeNode` hash methods).
//!
//! Upstream hashes three strings per element with SHA-256 and keeps the first
//! 16 hex characters as an integer (`int(hex[:16], 16)`, i.e. the first eight
//! bytes big-endian). The Python adapter assembles the exact strings upstream
//! would hash and this module does the hashing in one batch.

use pyo3::prelude::*;
use sha2::{Digest, Sha256};

/// First 16 hex chars of SHA-256 as an integer: the top eight digest bytes, big-endian.
#[must_use]
pub fn sha256_prefix_u64(input: &str) -> u64 {
    let digest = Sha256::digest(input.as_bytes());
    let mut top = [0u8; 8];
    top.copy_from_slice(&digest[..8]);
    u64::from_be_bytes(top)
}

/// Hash every string in `inputs`, preserving order.
#[must_use]
pub fn hash_batch(inputs: &[String]) -> Vec<u64> {
    inputs.iter().map(|s| sha256_prefix_u64(s)).collect()
}

/// Batched SHA-256 prefixes for the strings upstream hashes (element, stable, parent branch).
#[pyfunction]
pub fn element_hashes_flat(py: Python<'_>, inputs: Vec<String>) -> Vec<u64> {
    py.detach(|| hash_batch(&inputs))
}

#[cfg(test)]
mod tests {
    use super::{hash_batch, sha256_prefix_u64};

    #[test]
    fn matches_python_int_of_hex_prefix() {
        // hashlib.sha256(b"a|b").hexdigest()[:16] == "ab4d6f0d0e1b0f9a" is NOT assumed;
        // instead check against the known digest of the empty string:
        // e3b0c44298fc1c14 9afbf4c8996fb924 ... -> 0xe3b0c44298fc1c14
        assert_eq!(sha256_prefix_u64(""), 0xe3b0_c442_98fc_1c14);
        // "abc" -> ba7816bf8f01cfea ...
        assert_eq!(sha256_prefix_u64("abc"), 0xba78_16bf_8f01_cfea);
    }

    #[test]
    fn batch_preserves_order_and_length() {
        let out = hash_batch(&["".to_string(), "abc".to_string()]);
        assert_eq!(out, vec![0xe3b0_c442_98fc_1c14, 0xba78_16bf_8f01_cfea]);
        assert!(hash_batch(&[]).is_empty());
    }
}
