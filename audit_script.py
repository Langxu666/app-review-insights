"""
Comprehensive audit script for localhost:3000
Uses Playwright to perform browser automation, screenshots, console checks,
accessibility audit, and performance analysis.
"""
import json
import time
import os
from playwright.sync_api import sync_playwright

OUTPUT_DIR = "e:/app-review-insights/final"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            device_scale_factor=1,
        )
        page = context.new_page()

        # Collect console messages
        console_messages = []
        page.on("console", lambda msg: console_messages.append({
            "type": msg.type,
            "text": msg.text,
            "location": msg.location
        }))

        # Collect page errors
        page_errors = []
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        print("=" * 60)
        print("STEP 1: Navigate to localhost:3000 and take initial screenshot")
        print("=" * 60)

        page.goto("http://localhost:3000", wait_until="networkidle", timeout=30000)
        # Wait a moment for any dynamic content to render
        page.wait_for_timeout(3000)

        # Take initial screenshot
        initial_path = os.path.join(OUTPUT_DIR, "initial_screenshot.png")
        page.screenshot(path=initial_path, full_page=True)
        print(f"Initial screenshot saved to: {initial_path}")

        # Get page title
        title = page.title()
        print(f"Page title: {title}")

        print("\n" + "=" * 60)
        print("STEP 2: Check console messages")
        print("=" * 60)

        # Filter console messages
        errors = [m for m in console_messages if m["type"] == "error"]
        warnings = [m for m in console_messages if m["type"] == "warning"]
        logs = [m for m in console_messages if m["type"] == "log"]

        print(f"Total console messages: {len(console_messages)}")
        print(f"Errors: {len(errors)}")
        print(f"Warnings: {len(warnings)}")
        print(f"Logs: {len(logs)}")
        print(f"Page errors (uncaught): {len(page_errors)}")

        for e in errors:
            print(f"  CONSOLE ERROR: {e['text']}")
        for w in warnings:
            print(f"  CONSOLE WARNING: {w['text']}")
        for pe in page_errors:
            print(f"  PAGE ERROR: {pe}")

        print("\n" + "=" * 60)
        print("STEP 3: Trigger the analysis workflow")
        print("=" * 60)

        # Find the input field for App Store URL
        # Try various selectors to find the input field
        input_selectors = [
            'input[placeholder*="App Store"]',
            'input[placeholder*="URL"]',
            'input[placeholder*="url"]',
            'input[placeholder*="app"]',
            'input[type="text"]',
            'input[type="url"]',
            'input:not([type="hidden"])',
            'textarea',
        ]

        input_element = None
        used_selector = None
        for selector in input_selectors:
            try:
                el = page.locator(selector).first
                if el.is_visible(timeout=500):
                    input_element = el
                    used_selector = selector
                    print(f"Found input using selector: {selector}")
                    placeholder = el.get_attribute("placeholder")
                    print(f"  Placeholder: {placeholder}")
                    break
            except:
                continue

        if input_element:
            # Clear and type the URL
            input_element.click()
            input_element.fill("")
            app_url = "https://apps.apple.com/us/app/workout-for-women-home-gym/id839285684"
            input_element.type(app_url, delay=50)
            print(f"Typed App Store URL: {app_url}")
            page.wait_for_timeout(500)

            # Find and click the Analyze button
            button_selectors = [
                'button:has-text("Analyze")',
                'button:has-text("analyze")',
                'button:has-text("分析")',
                'button:has-text("Submit")',
                'button[type="submit"]',
                'button',
            ]

            analyze_button = None
            for btn_selector in button_selectors:
                try:
                    btn = page.locator(btn_selector).first
                    if btn.is_visible(timeout=500):
                        btn_text = btn.text_content()
                        print(f"Found button: '{btn_text}' using selector: {btn_selector}")
                        analyze_button = btn
                        break
                except:
                    continue

            if analyze_button:
                analyze_button.click()
                print("Clicked Analyze button")

                # Wait for analysis to complete - up to 120 seconds
                print("Waiting for analysis to complete (up to 120 seconds)...")
                start_time = time.time()
                max_wait = 120

                # Check for various completion indicators
                completed = False
                while time.time() - start_time < max_wait:
                    elapsed = time.time() - start_time
                    if elapsed % 10 < 0.5:  # Print progress every 10 seconds
                        print(f"  Waiting... {int(elapsed)}s elapsed")

                    # Check for completion indicators
                    try:
                        # Look for success/result indicators
                        if page.locator('text=complete').count() > 0 or \
                           page.locator('text=Complete').count() > 0 or \
                           page.locator('text=Done').count() > 0 or \
                           page.locator('text=done').count() > 0 or \
                           page.locator('text=Results').count() > 0 or \
                           page.locator('[data-testid="result"]').count() > 0 or \
                           page.locator('.result').count() > 0 or \
                           page.locator('text=Score').count() > 0 or \
                           page.locator('text=Reviews').count() > 0:
                            print(f"  Completion indicator found at {int(elapsed)}s")
                            completed = True
                            break
                    except:
                        pass

                    # Also check if any error appeared
                    try:
                        if page.locator('text=Error').count() > 0 or \
                           page.locator('text=Failed').count() > 0:
                            error_text = page.locator('text=Error').first.text_content() if page.locator('text=Error').count() > 0 else "Unknown"
                            print(f"  Error detected: {error_text}")
                            break
                    except:
                        pass

                    page.wait_for_timeout(1000)

                if not completed:
                    print(f"  Analysis may still be in progress after {int(time.time() - start_time)}s")

                # Wait a bit more for final rendering
                page.wait_for_timeout(3000)

                # Take screenshot after workflow
                workflow_path = os.path.join(OUTPUT_DIR, "workflow_result_screenshot.png")
                page.screenshot(path=workflow_path, full_page=True)
                print(f"Workflow result screenshot saved to: {workflow_path}")
            else:
                print("WARNING: Could not find Analyze button")
                # List all buttons for debugging
                all_buttons = page.locator('button').all()
                for i, btn in enumerate(all_buttons):
                    try:
                        print(f"  Button {i}: '{btn.text_content()}'")
                    except:
                        pass
        else:
            print("WARNING: Could not find App Store URL input field")
            # Print page content for debugging
            page_text = page.locator('body').text_content()
            print(f"Page body preview: {page_text[:500]}")
            # Take debug screenshot
            debug_path = os.path.join(OUTPUT_DIR, "debug_no_input.png")
            page.screenshot(path=debug_path, full_page=True)
            print(f"Debug screenshot saved to: {debug_path}")

        # Collect any new console messages
        print("\n" + "=" * 60)
        print("STEP 4: Accessibility Audit")
        print("=" * 60)

        accessibility_results = page.evaluate("""() => {
            const results = [];
            // Check for images without alt text
            document.querySelectorAll('img:not([alt])').forEach(el => results.push('IMG missing alt: ' + (el.src || 'no src')));
            // Check for form inputs without labels
            document.querySelectorAll('input:not([aria-label]):not([aria-labelledby])').forEach(el => {
                const hasLabel = el.closest('label') || document.querySelector(`label[for="${el.id}"]`);
                if (!hasLabel && el.type !== 'hidden' && el.type !== 'submit') results.push('INPUT missing label: ' + (el.placeholder || el.name || el.id || 'unknown'));
            });
            // Check heading hierarchy
            const headings = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')];
            let prevLevel = 0;
            headings.forEach(h => {
                const level = parseInt(h.tagName[1]);
                if (level > prevLevel + 1 && prevLevel > 0) results.push(`Heading skip: h${prevLevel} to h${level} - "${h.textContent.substring(0,50)}"`);
                prevLevel = level;
            });
            // Check for ARIA roles on interactive elements
            const interactiveWithoutRole = [...document.querySelectorAll('button:not([role]), a:not([role]), [onclick]:not([role])')].filter(el => {
                return !el.hasAttribute('role') && !el.hasAttribute('aria-label');
            });
            if (interactiveWithoutRole.length > 10) results.push(`Many interactive elements without ARIA: ${interactiveWithoutRole.length}`);
            // Check for skip link
            if (!document.querySelector('a[href="#main"], [role="main"]')) results.push('No skip link or main landmark found');
            return { issues: results, totalIssues: results.length };
        }""")

        print(f"Accessibility issues found: {accessibility_results['totalIssues']}")
        for issue in accessibility_results['issues']:
            print(f"  - {issue}")

        print("\n" + "=" * 60)
        print("STEP 5: Performance Check")
        print("=" * 60)

        performance_results = page.evaluate("""() => {
            const perf = performance.getEntriesByType('navigation')[0];
            const paint = performance.getEntriesByType('paint');
            const fcp = paint.find(p => p.name === 'first-contentful-paint');
            const resources = performance.getEntriesByType('resource');
            const totalResources = resources.length;
            const largeResources = resources.filter(r => r.transferSize > 100000).length;
            const domNodes = document.querySelectorAll('*').length;
            return {
                domContentLoaded: perf ? perf.domContentLoadedEventEnd - perf.fetchStart : 0,
                loadComplete: perf ? perf.loadEventEnd - perf.fetchStart : 0,
                firstContentfulPaint: fcp ? fcp.startTime : 0,
                totalResources: totalResources,
                largeResources: largeResources,
                domNodes: domNodes,
                transferSize: resources.reduce((sum, r) => sum + (r.transferSize || 0), 0),
            };
        }""")

        print(f"DOM Content Loaded: {performance_results['domContentLoaded']:.2f}ms")
        print(f"Load Complete: {performance_results['loadComplete']:.2f}ms")
        print(f"First Contentful Paint: {performance_results['firstContentfulPaint']:.2f}ms")
        print(f"Total Resources: {performance_results['totalResources']}")
        print(f"Large Resources (>100KB): {performance_results['largeResources']}")
        print(f"DOM Nodes: {performance_results['domNodes']}")
        print(f"Total Transfer Size: {performance_results['transferSize']} bytes ({performance_results['transferSize']/1024:.1f} KB)")

        print("\n" + "=" * 60)
        print("STEP 6: Final full-page screenshot")
        print("=" * 60)

        final_path = os.path.join(OUTPUT_DIR, "final_screenshot.png")
        page.screenshot(path=final_path, full_page=True)
        print(f"Final screenshot saved to: {final_path}")

        # Get page HTML snapshot for analysis
        print("\n" + "=" * 60)
        print("STEP 7: Page structure analysis")
        print("=" * 60)

        # Check for key UI elements
        elements_check = page.evaluate("""() => {
            const checks = {};
            checks.headings = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].map(h => ({
                tag: h.tagName,
                text: h.textContent.substring(0, 80)
            }));
            checks.buttons = [...document.querySelectorAll('button')].map(b => ({
                text: b.textContent.substring(0, 50),
                disabled: b.disabled
            }));
            checks.inputs = [...document.querySelectorAll('input, textarea')].map(i => ({
                tag: i.tagName,
                type: i.type || 'textarea',
                placeholder: i.placeholder || '',
                name: i.name || '',
                id: i.id || ''
            }));
            checks.links = [...document.querySelectorAll('a')].map(a => ({
                text: a.textContent.substring(0, 50),
                href: a.href
            }));
            checks.images = document.querySelectorAll('img').length;
            return checks;
        }""")

        print(f"Images on page: {elements_check['images']}")
        print(f"Headings found: {len(elements_check['headings'])}")
        for h in elements_check['headings']:
            print(f"  {h['tag']}: {h['text']}")
        print(f"Buttons found: {len(elements_check['buttons'])}")
        for b in elements_check['buttons']:
            print(f"  Button: '{b['text']}' disabled={b['disabled']}")
        print(f"Inputs found: {len(elements_check['inputs'])}")
        for inp in elements_check['inputs']:
            print(f"  {inp['tag']}: type={inp['type']} placeholder='{inp['placeholder']}' name='{inp['name']}' id='{inp['id']}'")

        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        # Compile final report
        report = {
            "page_title": title,
            "initial_console_errors": len(errors),
            "initial_console_warnings": len(warnings),
            "page_errors": len(page_errors),
            "console_error_details": [e['text'] for e in errors],
            "console_warning_details": [w['text'] for w in warnings],
            "page_error_details": page_errors,
            "accessibility_issues": accessibility_results['totalIssues'],
            "accessibility_details": accessibility_results['issues'],
            "performance": {
                "domContentLoaded_ms": round(performance_results['domContentLoaded'], 2),
                "loadComplete_ms": round(performance_results['loadComplete'], 2),
                "fcp_ms": round(performance_results['firstContentfulPaint'], 2),
                "total_resources": performance_results['totalResources'],
                "large_resources": performance_results['largeResources'],
                "dom_nodes": performance_results['domNodes'],
                "transfer_size_kb": round(performance_results['transferSize'] / 1024, 1),
            },
            "ui_elements": {
                "headings_count": len(elements_check['headings']),
                "buttons_count": len(elements_check['buttons']),
                "inputs_count": len(elements_check['inputs']),
                "images_count": elements_check['images'],
            }
        }

        # Save report
        report_path = os.path.join(OUTPUT_DIR, "audit_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"Audit report saved to: {report_path}")
        print(json.dumps(report, indent=2))

        browser.close()

if __name__ == "__main__":
    main()