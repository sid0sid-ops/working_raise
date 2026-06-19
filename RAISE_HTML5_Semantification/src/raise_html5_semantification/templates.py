DOCUMENT_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }}</title>
  <style>
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.55;
      margin: 0;
      color: #17202a;
      background: #fafafa;
    }
    header, main, footer { max-width: 960px; margin: 0 auto; padding: 1.25rem; }
    header { border-bottom: 1px solid #d8dee4; background: #fff; }
    main { background: #fff; }
    section { margin: 1.25rem 0; padding-top: 0.25rem; }
    h1, h2, h3 { line-height: 1.2; margin: 1rem 0 0.5rem; }
    p, aside, ul, ol, table { margin: 0.75rem 0; }
    aside { border-left: 4px solid #b6bec9; padding: 0.5rem 0.75rem; background: #f3f5f7; }
    table { border-collapse: collapse; width: 100%; display: block; overflow-x: auto; }
    th, td {
      border: 1px solid #c9d1d9;
      padding: 0.45rem 0.6rem;
      text-align: left;
      vertical-align: top;
    }
    th { background: #f0f3f6; }
    pre {
      white-space: pre-wrap;
      background: #f6f8fa;
      padding: 0.75rem;
      border: 1px solid #d8dee4;
      overflow-x: auto;
    }
    .metadata { color: #57606a; font-size: 0.95rem; }
    nav ol { padding-left: 1.4rem; }
    article { display: block; }
  </style>
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "DigitalDocument",
    "name": "{{ title }}",
    "creator": "Siddharth Tripathi",
    "encodingFormat": "text/html",
    "isBasedOn": "Prepared annual-report block JSON"
  }
  </script>
</head>
<body>
  <header role="banner">
    <h1>RAISE HTML5 Semantification Output</h1>
    <p class="metadata">
      Generated from prepared annual-report block JSON.
      This file preserves traceability through data attributes.
    </p>
{{ outline }}
  </header>
  <main id="report-content" role="main" aria-label="Semantic annual report content">
    <article id="semantic-report" aria-label="Semantified annual report">
{{ body }}
    </article>
  </main>
  <footer role="contentinfo">
    <p class="metadata">
      Module owner: Siddharth Tripathi.
      Next stage input variable: <code>semantic_html_path</code>.
    </p>
  </footer>
</body>
</html>
"""
