"""
Comprehensive audit script for localhost:3000 using Selenium with Edge WebDriver
"""
import json
import time
import os
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException

OUTPUT_DIR = "e:/app-review-insights/final"

def main():
    print("Setting up Edge WebDriver...")
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    
    # Suppress logging
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    
    service = Service(EdgeChromiumDriverManager().install())
    driver = webdriver.Edge(service=service, options=options)
    
    console_logs = []
    
    try:
        print("=" * 60)
        print("STEP 1: Navigate to localhost:3000 and take initial screenshot")
        print("=" * 60)
        
        driver.get("http://localhost:3000")
        time.sleep(3)
        
        # Take initial screenshot
        initial_path = os.path.join(OUTPUT_DIR, "initial_screenshot.png")
        driver.save_screenshot(initial_path)
        print(f"Initial screenshot saved to: {initial_path}")
        
        title = driver.title
        print(f"Page title: {title}")
        
        print("\n" + "=" * 60)
        print("STEP 2: Check console messages")
        print("=" * 60)
        
        # Get browser logs (console errors)
        try:
            logs = driver.get_log("browser")
            errors = [l for l in logs if l['level'] == 'SEVERE']
            warnings = [l for l in logs if l['level'] == 'WARNING']
            print(f"Browser log entries: {len(logs)}")
            print(f"Errors (SEVERE): {len(errors)}")
            print(f"Warnings: {len(warnings)}")
            for e in errors:
                print(f"  ERROR: {e['message']}")
            for w in warnings:
                print(f"  WARNING: {w['message']}")
        except Exception as e:
            print(f"  Could not retrieve browser logs: {e}")
        
        print("\n" + "=" * 60)
        print("STEP 3: Trigger the analysis workflow")
        print("=" * 60)
        
        # Find the input field
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
        for selector in input_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    if el.is_displayed():
                        input_element = el
                        print(f"Found input using selector: {selector}")
                        placeholder = el.get_attribute("placeholder")
                        print(f"  Placeholder: {placeholder}")
                        break
                if input_element:
                    break
            except:
                continue
        
        if input_element:
            input_element.click()
            input_element.clear()
            app_url = "https://apps.apple.com/us/app/workout-for-women-home-gym/id839285684"
            input_element.send_keys(app_url)
            print(f"Typed App Store URL: {app_url}")
            time.sleep(0.5)
            
            # Find and click Analyze button
            button_selectors = [
                'button:has-text("Analyze")' if False else 'button',
            ]
            
            # Try to find buttons by text
            all_buttons = driver.find_elements(By.CSS_SELECTOR, 'button')
            analyze_button = None
            for btn in all_buttons:
                try:
                    btn_text = btn.text.strip()
                    print(f"  Found button: '{btn_text}' disabled={not btn.is_enabled()}")
                    if 'analyze' in btn_text.lower() or 'analyse' in btn_text.lower() or 'submit' in btn_text.lower() or 'search' in btn_text.lower() or 'go' == btn_text.lower():
                        analyze_button = btn
                        print(f"  -> Selected as analyze button: '{btn_text}'")
                        break
                except:
                    pass
            
            if not analyze_button and all_buttons:
                # Try to find any submit-like button
                analyze_button = all_buttons[0] if len(all_buttons) == 1 else None
                if analyze_button:
                    print(f"  -> Using only button: '{analyze_button.text}'")
            
            if analyze_button:
                analyze_button.click()
                print("Clicked Analyze button")
                
                # Wait for analysis
                print("Waiting for analysis to complete (up to 120 seconds)...")
                start_time = time.time()
                max_wait = 120
                completed = False
                
                while time.time() - start_time < max_wait:
                    elapsed = time.time() - start_time
                    if int(elapsed) % 10 == 0 and int(elapsed) > 0:
                        print(f"  Waiting... {int(elapsed)}s elapsed")
                    
                    page_text = driver.find_element(By.TAG_NAME, 'body').text.lower()
                    
                    # Check for completion indicators
                    completion_keywords = ['complete', 'done', 'results', 'score', 'reviews', 'analysis']
                    for kw in completion_keywords:
                        if kw in page_text:
                            print(f"  Completion indicator '{kw}' found at {int(elapsed)}s")
                            completed = True
                            break
                    
                    if completed:
                        break
                    
                    # Check for errors
                    if 'error' in page_text.lower() or 'failed' in page_text.lower():
                        print(f"  Error indicator found at {int(elapsed)}s")
                        break
                    
                    time.sleep(1)
                
                if not completed:
                    print(f"  Analysis may still be in progress after {int(time.time() - start_time)}s")
                
                time.sleep(3)
                
                # Take screenshot after workflow
                workflow_path = os.path.join(OUTPUT_DIR, "workflow_result_screenshot.png")
                driver.save_screenshot(workflow_path)
                print(f"Workflow result screenshot saved to: {workflow_path}")
            else:
                print("WARNING: Could not find Analyze button")
        else:
            print("WARNING: Could not find App Store URL input field")
            # Print page content for debugging
            body_text = driver.find_element(By.TAG_NAME, 'body').text
            print(f"Page body preview: {body_text[:500]}")
            debug_path = os.path.join(OUTPUT_DIR, "debug_no_input.png")
            driver.save_screenshot(debug_path)
            print(f"Debug screenshot saved to: {debug_path}")
        
        print("\n" + "=" * 60)
        print("STEP 4: Accessibility Audit")
        print("=" * 60)
        
        accessibility_results = driver.execute_script("""
            const results = [];
            document.querySelectorAll('img:not([alt])').forEach(el => results.push('IMG missing alt: ' + (el.src || 'no src')));
            document.querySelectorAll('input:not([aria-label]):not([aria-labelledby])').forEach(el => {
                const hasLabel = el.closest('label') || document.querySelector('label[for="' + el.id + '"]');
                if (!hasLabel && el.type !== 'hidden' && el.type !== 'submit') results.push('INPUT missing label: ' + (el.placeholder || el.name || el.id || 'unknown'));
            });
            const headings = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')];
            let prevLevel = 0;
            headings.forEach(h => {
                const level = parseInt(h.tagName[1]);
                if (level > prevLevel + 1 && prevLevel > 0) results.push('Heading skip: h' + prevLevel + ' to h' + level + ' - "' + h.textContent.substring(0,50) + '"');
                prevLevel = level;
            });
            const interactiveWithoutRole = [...document.querySelectorAll('button:not([role]), a:not([role]), [onclick]:not([role])')].filter(el => {
                return !el.hasAttribute('role') && !el.hasAttribute('aria-label');
            });
            if (interactiveWithoutRole.length > 10) results.push('Many interactive elements without ARIA: ' + interactiveWithoutRole.length);
            if (!document.querySelector('a[href="#main"], [role="main"]')) results.push('No skip link or main landmark found');
            return { issues: results, totalIssues: results.length };
        """)
        
        print(f"Accessibility issues found: {accessibility_results['totalIssues']}")
        for issue in accessibility_results['issues']:
            print(f"  - {issue}")
        
        print("\n" + "=" * 60)
        print("STEP 5: Performance Check")
        print("=" * 60)
        
        performance_results = driver.execute_script("""
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
        """)
        
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
        driver.save_screenshot(final_path)
        print(f"Final screenshot saved to: {final_path}")
        
        print("\n" + "=" * 60)
        print("STEP 7: Page structure analysis")
        print("=" * 60)
        
        elements_check = driver.execute_script("""
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
        """)
        
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
        
        report = {
            "page_title": title,
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
        
        report_path = os.path.join(OUTPUT_DIR, "audit_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"Audit report saved to: {report_path}")
        print(json.dumps(report, indent=2))
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()