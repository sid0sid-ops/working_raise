//! PDF line-break hyphen repair.

use regex::Regex;
use std::sync::OnceLock;

static HYPHEN_BREAK_RE: OnceLock<Regex> = OnceLock::new();

fn get_hyphen_break_re() -> &'static Regex {
    HYPHEN_BREAK_RE.get_or_init(|| Regex::new(r"(\b[a-zA-Z]{2,})-\s*\n\s*([a-zA-Z]{2,}\b)").unwrap())
}

/// Repairs broken hyphenated words split across line breaks in extracted PDFs.
/// e.g. "infra-\nstructure" -> "infrastructure"
pub fn repair_hyphenation(input: &str) -> String {
    if input.is_empty() {
        return String::new();
    }

    get_hyphen_break_re().replace_all(input, "$1$2").into_owned()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_repair_hyphenation() {
        let raw = "The deep-tech infra-\n   structure at IITMRP supports micro-\ncontrollers.";
        let repaired = repair_hyphenation(raw);
        assert_eq!(repaired, "The deep-tech infrastructure at IITMRP supports microcontrollers.");
    }
}
