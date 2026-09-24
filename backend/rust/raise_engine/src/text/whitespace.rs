//! High-speed whitespace consolidation and paragraph cleanup.

use regex::Regex;
use std::sync::OnceLock;

static MULTI_SPACE_RE: OnceLock<Regex> = OnceLock::new();
static MULTI_NEWLINE_RE: OnceLock<Regex> = OnceLock::new();

fn get_multi_space_re() -> &'static Regex {
    MULTI_SPACE_RE.get_or_init(|| Regex::new(r"[ \t]+").unwrap())
}

fn get_multi_newline_re() -> &'static Regex {
    MULTI_NEWLINE_RE.get_or_init(|| Regex::new(r"\n{3,}").unwrap())
}

/// Collapses redundant spaces and tabs, trims trailing whitespace on lines,
/// and compresses excessive blank lines (more than 2 consecutive newlines) into 2.
pub fn cleanup_whitespace(input: &str) -> String {
    if input.is_empty() {
        return String::new();
    }

    let mut lines = Vec::new();
    for line in input.lines() {
        let trimmed_line = line.trim();
        if trimmed_line.is_empty() {
            lines.push("");
        } else {
            let collapsed = get_multi_space_re().replace_all(trimmed_line, " ");
            lines.push(collapsed.into_owned().leak());
        }
    }

    let joined = lines.join("\n");
    get_multi_newline_re().replace_all(&joined, "\n\n").into_owned()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_whitespace_cleanup() {
        let raw = "This   is   a    test.   \n\n\n\nAnother    paragraph  here.\n";
        let cleaned = cleanup_whitespace(raw);
        assert_eq!(cleaned, "This is a test.\n\nAnother paragraph here.");
    }
}
