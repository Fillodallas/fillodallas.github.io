#!/usr/bin/env python3
"""
Generate a PDF from the CV HTML using Chromium/Playwright.

The HTML remains the single source of truth for the CV styling.

Usage:
    python generate_pdf.py

Requirements:
    pip install playwright
    python -m playwright install chromium
"""

from pathlib import Path
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent
HTML_FILE = ROOT / "index.html"
PDF_FILE = ROOT / "Filippo_DallAsta_CV.pdf"

# Match the desktop width used by the CV.
VIEWPORT_WIDTH = 980


def main() -> None:
    if not HTML_FILE.exists():
        raise FileNotFoundError(f"Could not find: {HTML_FILE}")

    with sync_playwright() as p:
        browser = p.chromium.launch()

        page = browser.new_page(
            viewport={"width": VIEWPORT_WIDTH, "height": 1000},
            device_scale_factor=1,
        )

        page.goto(HTML_FILE.as_uri(), wait_until="networkidle")

        # Make sure Google fonts / locally available fonts have finished loading.
        page.evaluate("document.fonts.ready")

        # ---------------------------------------------------------------
        # PDF-only adjustments
        # ---------------------------------------------------------------
        #
        # The website has a small animated "boot" line at the top of the
        # hero section. It is a web-only visual and is intentionally removed
        # from the PDF rather than rendered as static text.
        #
        # Removing it also reduces the document height, helping prevent an
        # unnecessary second page.
        page.evaluate("""
            () => {
                const boot = document.getElementById('boot');
                if (boot) {
                    boot.remove();
                }

                // Prevent any animation/transition from affecting the
                // dimensions or appearance of the generated PDF.
                const style = document.createElement('style');
                style.textContent = `
                    *,
                    *::before,
                    *::after {
                        animation: none !important;
                        transition: none !important;
                    }

                    @page {
                        margin: 0;
                    }
                `;
                document.head.appendChild(style);
            }
        """)

        # Give the browser one rendering pass after the PDF-only changes.
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(50)

        # ---------------------------------------------------------------
        # Measure the final rendered CV
        # ---------------------------------------------------------------
        dimensions = page.evaluate("""
            () => {
                const body = document.body;
                const html = document.documentElement;

                return {
                    width: Math.max(
                        body.scrollWidth,
                        body.offsetWidth,
                        html.scrollWidth,
                        html.offsetWidth
                    ),
                    height: Math.max(
                        body.scrollHeight,
                        body.offsetHeight,
                        html.scrollHeight,
                        html.offsetHeight
                    )
                };
            }
        """)

        pdf_width = dimensions["width"]

        # Add a tiny safety margin to avoid a Chromium rounding issue where
        # content exactly on the final pixel can spill onto a second page.
        pdf_height = dimensions["height"] + 2

        # Explicitly tell Chromium that the PDF page itself has this exact
        # size. This avoids normal A4/Letter pagination entirely.
        page.add_style_tag(
            content=f"""
                @page {{
                    size: {pdf_width}px {pdf_height}px;
                    margin: 0;
                }}

                html, body {{
                    margin: 0 !important;
                    padding: 0 !important;
                }}
            """
        )

        page.pdf(
            path=str(PDF_FILE),
            width=f"{pdf_width}px",
            height=f"{pdf_height}px",
            print_background=True,
            margin={
                "top": "0px",
                "right": "0px",
                "bottom": "0px",
                "left": "0px",
            },
            display_header_footer=False,
            prefer_css_page_size=False,
            scale=1,
        )

        browser.close()

    print(f"PDF generated: {PDF_FILE}")
    print(f"Rendered size: {pdf_width} × {pdf_height - 2} CSS px")


if __name__ == "__main__":
    main()
