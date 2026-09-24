//! Fast Unicode normalization, character sanitization, and cleanups.

use regex::Regex;
use std::sync::OnceLock;

static CONTROL_CHAR_RE: OnceLock<Regex> = OnceLock::new();
static SMART_QUOTES_RE: OnceLock<Vec<(Regex, &'static str)>> = OnceLock::new();

fn get_control_char_re() -> &'static Regex {
    CONTROL_CHAR_RE.get_or_init(|| Regex::new(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]").unwrap())
}

fn get_smart_quotes_re() -> &'static [(Regex, &'static str)] {
    SMART_QUOTES_RE.get_or_init(|| {
        vec![
            (Regex::new(r"[\u2018\u2019\u201A\u201B`´]").unwrap(), "'"),
            (Regex::new(r"[\u201C\u201D\u201E\u201F«»]").unwrap(), "\""),
            (Regex::new(r"[\u2013\u2014\u2015]").unwrap(), "-"),
            (Regex::new(r"\u2026").unwrap(), "..."),
            (Regex::new(r"[\u00A0\u2000-\u200B\u202F\u205F\u3000]").unwrap(), " "),
            (Regex::new(r"\r\n|\r").unwrap(), "\n"),
        ]
    })
}

/// Normalizes text by removing non-printable control characters, replacing smart quotes/dashes,
/// and harmonizing line breaks.
pub fn normalize_text(input: &str) -> String {
    if input.is_empty() {
        return String::new();
    }

    let mut result = input.to_string();

    // 1. Remove non-printable control characters
    result = get_control_char_re().replace_all(&result, "").into_owned();

    // 2. Replace typographic quotes, dashes, non-breaking spaces
    for (re, replacement) in get_smart_quotes_re() {
        result = re.replace_all(&result, *replacement).into_owned();
    }

    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_normalize_smart_quotes_and_dashes() {
        let raw = "\u{201C}Hello\u{201D} \u{2014} \u{2018}world\u{2019}\u{2026}\r\nSecond line\u{00A0}here.";
        let norm = normalize_text(raw);
        assert_eq!(norm, "\"Hello\" - 'world'...\nSecond line here.");
    }
}
