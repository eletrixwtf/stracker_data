import json
from playwright.sync_api import sync_playwright

def main():
    print("🚀 ==========================================")
    print("🚀 Starting Steam-Tracker Games Scraper")
    print("🚀 ==========================================")

    games_list_url = "https://steam-tracker.com/apps/delisted"
    print(f"🔍 Fetching games list from {games_list_url}...")

    games = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--disable-gpu', '--no-sandbox'])
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
            page = context.new_page()
            page.goto(games_list_url, wait_until="domcontentloaded", timeout=30000)

            # Wait for the DataTable to initialize
            try:
                page.wait_for_selector('#delisted-apps tbody tr', timeout=15000)
            except Exception:
                print("⚠️ Could not find initial table rows, continuing anyway...")

            # Change "Show () entries" dropdown to "All" (value = -1)
            try:
                page.wait_for_selector('select[name="delisted-apps_length"]', timeout=10000)
                page.select_option('select[name="delisted-apps_length"]', "-1")
                print("✅ Set entries dropdown to 'All'")
            except Exception as e:
                print(f"⚠️ Could not set dropdown to All: {e}")

            # Wait for DataTables to finish redrawing with all rows.
            # We poll the row count until it stabilizes (stops growing) since
            # DataTables re-renders the whole tbody after the option changes.
            page.wait_for_timeout(1000)
            prev_count = -1
            stable_checks = 0
            for _ in range(60):  # up to ~30s
                count = page.eval_on_selector_all('#delisted-apps tbody tr', 'els => els.length')
                if count == prev_count:
                    stable_checks += 1
                    if stable_checks >= 3:
                        break
                else:
                    stable_checks = 0
                prev_count = count
                page.wait_for_timeout(500)

            print(f"📊 Row count stabilized at {prev_count}")

            # Extract appid + name from every row in the table body
            extracted = page.eval_on_selector_all(
                '#delisted-apps tbody tr[data-appid]',
                """els => els.map(el => {
                    const appid = el.getAttribute('data-appid');
                    const nameLink = el.querySelector('td:nth-child(3) a:last-of-type');
                    const name = nameLink ? nameLink.textContent.trim() : null;
                    return { appid, name };
                })"""
            )

            browser.close()

        # Clean up: dedupe, require valid appid + name
        seen = set()
        for item in extracted:
            appid_raw = item.get('appid')
            name = item.get('name')
            if not appid_raw or not name:
                continue
            try:
                appid = int(appid_raw)
            except ValueError:
                continue
            if appid in seen:
                continue
            seen.add(appid)
            games.append({"appid": appid, "name": name})

        print(f"✅ Found {len(games)} unique games on Steam-Tracker")

    except Exception as e:
        print(f"❌ Failed to fetch games list: {e}")
        with open("games_list.json", "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        return

    if not games:
        print("❌ No games found. Exiting.")
        with open("games_list.json", "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        return

    print("💾 Saving to games_list.json...")
    with open("games_list.json", "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2)
    print("✅ Saved successfully!")

if __name__ == "__main__":
    main()
