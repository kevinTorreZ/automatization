from playwright.sync_api import sync_playwright
import time
import random
import os

class BubloxUploader:
    def __init__(self, headless=True):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.email = None
        self.password = None

    def start(self):
        """Starts the browser session."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

    def login(self, email, password):
        """Logs into Bublox with provided credentials."""
        self.email = email
        self.password = password
        print("  [Bublox] Navigating to home page for login...")
        try:
            # Login is on the home page if not authenticated
            self.page.goto("https://bublox-3b380.web.app/") 
            self.page.wait_for_load_state("networkidle")
            
            # Check if login form is present
            if self.page.is_visible("text=Iniciar sesión") or self.page.is_visible("input[type='email']"):
                print("  [Bublox] Login form detected.")
                
                self.page.fill("input[type='email']", email)
                # Force update for React/Vue frameworks
                self.page.dispatch_event("input[type='email']", "input")
                self.page.dispatch_event("input[type='email']", "change")
                
                self.page.fill("input[type='password']", password)
                self.page.dispatch_event("input[type='password']", "input")
                self.page.dispatch_event("input[type='password']", "change")
                
                time.sleep(1) # Short wait for state update
                
                # Click login button
                # Click login button
                self.page.click("button[type='submit']")
                
                # Wait for navigation or UI update
                # After login, the form should disappear and "Crear nuevo Contenido" should appear
                try:
                    # Wait for either "Crear nuevo Contenido" OR the select element which confirms we are in.
                    self.page.wait_for_selector("text=Crear nuevo Contenido", state="visible", timeout=20000)
                    print("  [Bublox] Login successful (Dashboard detected).")
                except:
                    # Fallback check: sometimes text might be different, check for the main select
                    try:
                         self.page.wait_for_selector("select.inicio-select", state="attached", timeout=5000)
                         print("  [Bublox] Login successful (Select detected).")
                    except:
                        print("  [Bublox] Warning: Dashboard not detected after login.")
                        self.page.screenshot(path="debug_after_login.png")
            else:
                # Maybe already logged in?
                if self.page.is_visible("text=Crear nuevo Contenido") or self.page.is_visible("select.inicio-select"):
                    print("  [Bublox] Already logged in.")
                else:
                    print("  [Bublox] Login form NOT found and Dashboard NOT found.")
                    self.page.screenshot(path="debug_login_unknown.png")

        except Exception as e:
            print(f"  [Bublox] Login failed: {e}")
            self.page.screenshot(path="debug_login_error.png")

    def get_categories(self):
        """Fetches the list of available categories from the dropdown."""
        print("  [Bublox] Fetching categories...")
        try:
            if self.page.url != "https://bublox-3b380.web.app/" and self.page.url != "https://bublox-3b380.web.app":
                self.page.goto("https://bublox-3b380.web.app/")
                self.page.wait_for_load_state("networkidle")
            
            # Wait for select to be present
            self.page.wait_for_selector("select.inicio-select", timeout=10000)
            # Wait for at least one option (besides the placeholder)
            self.page.wait_for_function("document.querySelectorAll('select.inicio-select option').length > 1", timeout=10000)
            
            # Selector: select.inicio-select option
            # Use eval_on_selector_all to get values directly from DOM
            categories = self.page.eval_on_selector_all(
                "select.inicio-select option", 
                "elements => elements.map(e => e.value).filter(v => v !== '')"
            )
            
            print(f"  [Bublox] Found {len(categories)} categories.")
            return categories
        except Exception as e:
            print(f"  [Bublox] Error fetching categories: {e}")
            return []


    def upload_script(self, title, code, category):
        """
        Uploads a single script.
        """
        print(f"  [Bublox] Uploading: {title} (Category: {category})")
        try:
            # Ensure we are on the page (but don't force reload if already there)
            if self.page.url != "https://bublox-3b380.web.app/":
                self.page.goto("https://bublox-3b380.web.app/")
                self.page.wait_for_load_state("networkidle")
            
            # --- CLEAR FORM STATE ---
            print("  [Bublox] Clearing form state...")
            try:
                self.page.evaluate("""
                    // Clear Title
                    const title = document.querySelector("input[placeholder^='Título base']");
                    if (title) { title.value = ''; title.dispatchEvent(new Event('input', {bubbles: true})); }

                    // Clear Textarea
                    const area = document.querySelector("textarea.inicio-textarea");
                    if (area) { area.value = ''; area.dispatchEvent(new Event('input', {bubbles: true})); }

                    // Clear Select (Deselect all)
                    const select = document.querySelector("select.inicio-select");
                    if (select) {
                        select.selectedIndex = -1; 
                        select.value = "";
                        for (let i = 0; i < select.options.length; i++) {
                            select.options[i].selected = false;
                        }
                        select.dispatchEvent(new Event('change', {bubbles: true}));
                        select.dispatchEvent(new Event('input', {bubbles: true}));
                    }
                    
                    // --- REMOVE VISUAL TAGS ---
                    // The site uses visual tags (pills) with X buttons. We need to find and click them.
                    // Loop through buttons/icons that look like remove triggers near the select.
                    // Heuristic: Look for elements containing 'X' or SVGs within the form container or near the select.
                    
                    // Try to find the container of the tags. usually next to select.
                    // specific logic:
                    const removeButtons = Array.from(document.querySelectorAll("button, span, div, svg")).filter(el => {
                        // Check if it's a remove button
                        if (el.innerText === "✕" || el.innerText === "X" || el.classList.contains("remove") || el.classList.contains("close")) {
                            // Check visibility
                            const style = window.getComputedStyle(el);
                            if (style.display === 'none' || style.visibility === 'hidden') return false;
                            
                            // Check proximity to select (same form or container)
                            // This is risky, might click other close buttons.
                            // Let's be more targeted if possible.
                            return true;
                        }
                        return false;
                    });
                    
                    // Better approach: Look for the specific structure seen in screenshot
                    // Tags are below the select.
                    // Let's print the HTML structure for the python script to debug
                    // return document.querySelector("select.inicio-select").parentElement.parentElement.innerHTML;
                """)
                
                # Python side debug: Inspect content to find specific tag selector
                try:
                    # Get parent HTML of select to see where tags are
                    parent_html = self.page.eval_on_selector("select.inicio-select", "e => e.parentElement.parentElement.outerHTML")
                    print(f"  [Bublox] Debug: Select Container HTML: {parent_html[:500]}...") # Truncate

                    # Try to find and click "X" buttons based on common patterns
                    # If the tags are siblings or children of a container
                    # We can try a locator for the "X"
                    # Screenshot showed: [Category Name   X]
                    
                    # Try clicking anything that looks like a close interaction in that area
                    # Or specific class if we can guess.
                    # Let's try locating 'X' text or path
                    
                    # We will try to click all "X" or SVG buttons inside the container that holds the select?
                    # Or just query for text "✕"
                    
                    # Locator for the 'X' button
                    # Based on screenshot, maybe it's an SVG or text 'X'
                    # Let's try to find them by text "Selecciona una categoría" sibling
                    
                    # Use a locator that finds the text of the category and then the X?
                    # No, we want to clear ALL.
                    
                    # Generic clear: click all buttons that are red or have X?
                    # Let's try to just find standard close buttons.
                    
                    # Attempt to find close buttons
                    # Selector for "X" often:
                    close_btns = self.page.locator("text=✕").or_(self.page.locator("text=X")).all()
                    
                    # Filter for those that act as tags?
                    # This is dangerous.
                    
                    # Let's wait for the user to give me the HTML or I can just dump it now and ask.
                    pass
                except Exception as e:
                    print(f"  [Bublox] Debug Inspect Error: {e}")

                # Improved JS Clear Loop that targets the tags specifically
                # We know the structure:
                # <div>
                #   <label>Categorías:</label>
                #   <div><select ...></div>
                #   <div style="margin-top: 10px; display: flex; flex-wrap: wrap; gap: 8px;"> TAGS HERE </div>
                # </div>
                
                print("  [Bublox] Creating loop to clear tags from specific container...")
                self.page.evaluate("""
                    const select = document.querySelector("select.inicio-select");
                    if (select) {
                        try {
                            // 1. Find the container of the select (the div with gap: 10px)
                            const selectContainer = select.parentElement; 
                            // 2. Find the parent holding label, select-container, and TAGS container
                            const mainContainer = selectContainer.parentElement;
                            
                            // 3. Find the tags container. It should be the last child or the one with margin-top: 10px
                            // Let's iterate children of mainContainer
                            const children = Array.from(mainContainer.children);
                            let tagContainer = null;
                            
                            // Heuristic: It's a div, comes after selectContainer
                            for (let i = 0; i < children.length; i++) {
                                if (children[i] === selectContainer) {
                                    // Look at next siblings
                                    if (i + 1 < children.length) {
                                        tagContainer = children[i+1];
                                    }
                                    break;
                                }
                            }
                            
                            if (tagContainer) {
                                // console.log("Found tag container", tagContainer);
                                // 4. Remove all children of tag container (Click them if they are buttons, or find buttons inside)
                                // Actually, usually you click a 'remove' icon.
                                // If the tags are just divs, look for SVG or 'X' inside.
                                
                                const tags = tagContainer.querySelectorAll("*");
                                tags.forEach(el => {
                                    // If it's a button, click it.
                                    if (el.tagName === "BUTTON") {
                                        el.click();
                                    }
                                    // If it's an SVG, click its parent? or itself?
                                    else if (el.tagName === "svg") {
                                        el.parentElement.click(); // Click the button holding the SVG
                                        el.click(); // Or the SVG itself
                                    }
                                    // If it has "X" text
                                    else if (el.innerText && (el.innerText.trim() === "✕" || el.innerText.trim() === "X")) {
                                        el.click();
                                    }
                                });
                                
                                // Brute force: click everything in that container that looks interactive
                                const clickables = tagContainer.querySelectorAll("div, span, button, svg, path");
                                clickables.forEach(c => {
                                     // Check if it looks like a close button
                                     // Just click it if it's small?
                                     // This is risky if clicking the tag opens it?
                                     // User said "solo le deberia colocar el primero".
                                     // We want to DELETE.
                                });
                            }
                        } catch (err) {
                            console.log("JS Clear Error: " + err);
                        }
                    }
                """)
                
                # Python-side backup: Locator targeting that specific area
                # We can construct a locator based on layout
                # "select.inicio-select" -> parent -> parent -> last-child (or similar)
                
                try:
                    # div that contains the select
                    select_wrapper = self.page.locator("select.inicio-select").locator("xpath=..")
                    # The main container
                    main_wrapper = select_wrapper.locator("xpath=..")
                    # The tags container (sibling of select_wrapper)
                    # We assume it's the div after select_wrapper
                    tags_div = main_wrapper.locator("div").last
                    
                    # Count items in tags_div?
                    # We want to click "X" buttons inside here.
                    # Since we don't know exact selector for X, let's try generic "button" or "svg" inside tags_div
                    
                    # Wait for potential tags
                    time.sleep(1)
                    
                    # Click all buttons inside tags_div
                    buttons = tags_div.locator("button, svg").all()
                    if len(buttons) > 0:
                        print(f"  [Bublox] Found {len(buttons)} remove elements in tag container. Clicking...")
                        for btn in buttons:
                            if btn.is_visible():
                                btn.click(force=True, timeout=500)
                                time.sleep(0.1)
                except Exception as e:
                    print(f"  [Bublox] Python Clear Error: {e}")
            except Exception as e_clear:
                print(f"  [Bublox] Warning clearing form: {e_clear}")

            # DEBUG: Dump HTML of the form group to understand tag structure
            try:
                # content of the div wrapping the select and label
                html_debug = self.page.eval_on_selector("select.inicio-select", "e => e.parentElement.parentElement.innerHTML")
                print(f"  [Bublox] DEBUG FORM HTML: {html_debug}")
            except:
                pass
            
            # Python-side Aggressive Clear
            # Find all visible elements with text "✕" or "X" that are close to the select?
            # Or just all of them. The user says "MAX 1", so we want to kill all previous.
            # Be careful not to close the modal or something.
            
            # Let's try to click all "X" buttons that are NOT the main window close.
            # Heuristic: Small size?
            try:
                # Locator for X buttons
                # We expect them to be in the content area.
                x_buttons = self.page.locator("text=✕").or_(self.page.locator("text=X")).all()
                print(f"  [Bublox] Found {len(x_buttons)} potential 'X' buttons.")
                for btn in x_buttons:
                    try:
                        if btn.is_visible():
                            # Check if it's unrelated (e.g. top right of screen?)
                            # box = btn.bounding_box()
                            # if box['y'] < 50: continue # Skip top header
                            # Just click'em if they are likely tags
                             txt = btn.text_content()
                             if txt and txt.strip() in ["✕", "X"]:
                                 # print(f"  [Bublox] Clicking X button...")
                                 btn.click(timeout=1000)
                    except:
                        pass
            except:
                pass


            # <input placeholder="Título base (en español o inglés)" class="inicio-input">
            self.page.fill("input[placeholder^='Título base']", title)
            
            # 2. Click Generate
            # <button ...>Generar título/descr. (es/en) con IA</button>
            # It might be disabled briefly, but usually enabled after typing?
            # Or maybe we just click it.
            # Using force=True just in case, or waiting?
            # Let's try normal click.
            self.page.click("button:has-text('Generar título')")
            
            # 3. Wait ~7s (User request)
            print("  [Bublox] Waiting 8s for generation...")
            # Wait for generation to potentially finish
            time.sleep(8) 
            
            # Wait for select to be ENABLED
            print("  [Bublox] Waiting for category select to be enabled...")
            try:
                self.page.wait_for_function("document.querySelector('select.inicio-select') && !document.querySelector('select.inicio-select').disabled", timeout=10000)
                # Also wait for options to be populated
                self.page.wait_for_function("document.querySelectorAll('select.inicio-select option').length > 1", timeout=5000)
            except:
                print("  [Bublox] Warning: Timeout waiting for select/options.")

            # Check for multiple selects
            selects_count = self.page.locator("select.inicio-select").count()
            if selects_count > 1:
                print(f"  [Bublox] WARNING: Found {selects_count} select elements with class 'inicio-select'. Using the first visible one.")
            
            # 5. Select Category
            # <select class="inicio-select">
            print(f"  [Bublox] Selecting category: '{category}'")
            
            # Get current options
            try:
                options_data = self.page.eval_on_selector_all("select.inicio-select option", "opts => opts.map(o => ({text: o.innerText, value: o.value}))")
            except Exception as e:
                print(f"  [Bublox] Error fetching options: {e}")
                options_data = []

            target_index = -1
            target_value = category
            target_text = category # To verify against
            
            # Find match
            found_match_type = "None"
            for i, opt in enumerate(options_data):
                # exact value
                if opt['value'] == category:
                    target_index = i
                    target_value = opt['value']
                    target_text = opt['text']
                    found_match_type = "Exact Value"
                    break
                # exact text
                if opt['text'] == category:
                    target_index = i
                    target_value = opt['value']
                    target_text = opt['text']
                    found_match_type = "Exact Text"
                    break
                # case insensitive value
                if opt['value'].lower() == category.lower():
                    target_index = i
                    target_value = opt['value']
                    target_text = opt['text']
                    found_match_type = "Case Insensitive Value"
                    break
            
            # Fuzzy match if strict failed
            if target_index == -1:
                print(f"  [Bublox] Exact match for '{category}' not found. Trying fuzzy match...")
                for i, opt in enumerate(options_data):
                    if category.lower() in opt['text'].lower() or category.lower() in opt['value'].lower():
                         print(f"  [Bublox] Fuzzy match found: '{opt['text']}' (Index: {i})")
                         target_index = i
                         target_value = opt['value']
                         target_text = opt['text']
                         found_match_type = "Fuzzy"
                         break
            
            if target_index != -1:
                print(f"  [Bublox] Match Found: Type='{found_match_type}', TargetValue='{target_value}', TargetText='{target_text}'")
                try:
                    # Select by value if possible, it's more robust
                    if target_value:
                        self.page.select_option("select.inicio-select", value=target_value, timeout=5000)
                    else:
                        self.page.select_option("select.inicio-select", index=target_index, timeout=5000)
                    
                    # Double tap: Force dispatch events
                    self.page.evaluate("""
                        const select = document.querySelector('select.inicio-select');
                        if (select) {
                            select.dispatchEvent(new Event('change', { bubbles: true }));
                            select.dispatchEvent(new Event('input', { bubbles: true }));
                            select.dispatchEvent(new Event('blur', { bubbles: true }));
                        }
                    """)
                    
                except Exception as e_select:
                    print(f"  [Bublox] Standard select failed: {e_select}")
            else:
                 print(f"  [Bublox] ERROR: Category '{category}' NOT found (even with fuzzy match)!")
                 # Debug: Print all options
                 print(f"  [Bublox] Available options: {[o['text'] for o in options_data]}")
            
            # Check for multiple select attribute
            is_multiple = self.page.eval_on_selector("select.inicio-select", "e => e.multiple")
            if is_multiple:
                 print("  [Bublox] Info: Select element has 'multiple' attribute.")

            # 5. Fill Content/Notes
            # <textarea placeholder="Contenido/Notas (opcional)" class="inicio-textarea">
            self.page.fill("textarea.inicio-textarea", code)
            
            # --- VALIDATION ---
            print("  [Bublox] Validating form before creation...")
            
            # Check Category (Value or Text)
            cat_val = self.page.eval_on_selector("select.inicio-select", "e => e.value")
            
            # Use target_text if available, otherwise category
            check_text = target_text if target_text else category
            
            # Simplify check text for tag (remove placeid)
            # Tags often show "Blox fruits" instead of "Blox fruits (placeid: ...)"
            simple_check_text = check_text.split('(')[0].strip()

            # Check if TAG exists (Since select resets to empty on this site)
            # We look for an element containing the text of the category that is VISIBLE
            # The select option contains the text but is hidden.
            # We want to find the "Tag" or "Chip" that appears.
            
            # XPath to find text element that contains target_text
            # But exclude the option element itself?
            # options are usually inside the select.
            # We look for *other* elements.
            
            print(f"  [Bublox] Checking for tag existence: '{simple_check_text}' (Original: '{check_text}')")
            # We use a locator that matches text but is NOT an option
            # This is tricky as 'contains(text(), ...)' matches parents too.
            # Let's count how many elements contain the text.
            # If 1 (the option), then tag is missing.
            # If > 1, likely tag is present.
            
            def check_tag_presence():
                # Check for the simplified text
                count = self.page.locator(f"xpath=//*[contains(text(), '{simple_check_text}')]").count()
                # Debug
                # print(f"  [Bublox] Debug: Found {count} elements with text '{simple_check_text}'")
                return count > 1

            is_tag_present = check_tag_presence()

            # Retry Loop for Category
            retries = 3
            
            # Condition: Success if (Select Value matches) OR (Tag is Present)
            # Failure if (Select Value mismatch AND Tag missing)
            
            while (cat_val != target_value) and (not is_tag_present) and retries > 0:
                if "Selecciona una categor" in cat_val or cat_val == "":
                     print(f"  [Bublox] Warning: Placeholder selected and Tag not found. Retrying...")
                else:
                     print(f"  [Bublox] Warning: Checks failed (Val:'{cat_val}', TagPresent:{is_tag_present}). Retrying...")
                
                # ... (Refetch options code omitted for brevity as it was complex and maybe not needed if we rely on tag)
                # Let's just try setting it again.
                
                if target_index != -1:
                    # Strategy: JS Force Set by Value (Safer) or Index
                    print(f"  [Bublox] Retrying selection by value '{target_value}' (idx {target_index}) via JS...")
                    # Escape value for JS string
                    safe_val = target_value.replace("'", "\\'")
                    self.page.evaluate(f"""
                        const select = document.querySelector('select.inicio-select');
                        if (select) {{
                            // Try setting by value first
                            select.value = '{safe_val}';
                            if (select.value !== '{safe_val}') {{
                                // Fallback to index
                                select.selectedIndex = {target_index};
                            }}
                            select.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            select.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            select.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                        }}
                    """)
                time.sleep(1.5)
                cat_val = self.page.eval_on_selector("select.inicio-select", "e => e.value")
                is_tag_present = check_tag_presence()
                
                if is_tag_present:
                    print(f"  [Bublox] Tag detected for '{check_text}'. Assuming success.")
                    break
                    
                retries -= 1

            # Final check
            if is_tag_present:
                 print(f"  [Bublox] Validation Passed (Tag detected).")
            elif cat_val != target_value:
                 print(f"  [Bublox] WARNING: Category validation failed (No tag, Value mismatch). Proceeding anyway.")

            # print(f"  [Bublox] Validation Phase Complete.")

            # Check Title
            title_val = self.page.eval_on_selector("input[placeholder^='Título base']", "e => e.value")
            if not title_val or len(title_val.strip()) < 3:
                print(f"  [Bublox] Validation Failed: Title is empty or too short. ('{title_val}')")
                return 

            # 6. Click Create
            # <button type="submit" class="inicio-btn">Crear</button>
            # Use specific match because there are other buttons
            self.page.click("button[type='submit']:has-text('Crear')")
            
            time.sleep(3) 
            self.page.screenshot(path="debug_upload_success.png")
            print("  [Bublox] Upload complete.")
            
        except Exception as e:
            print(f"  [Bublox] Upload error: {e}")
            self.page.screenshot(path="debug_upload_error.png")

    def close(self):
        if self.context: self.context.close()
        if self.browser: self.browser.close()
        if self.playwright: self.playwright.stop()

