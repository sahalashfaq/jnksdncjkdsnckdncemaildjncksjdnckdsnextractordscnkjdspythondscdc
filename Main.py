import streamlit as st
import pandas as pd
import asyncio
import aiohttp
import re
import time
import json
import os
from bs4 import BeautifulSoup
from io import BytesIO
from urllib.parse import urljoin, urlparse
from collections import deque

# Load CSS
def load_css():
    try:
        with open("style.css") as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except:
        st.warning("No CSS loaded.")

load_css()

# Regex patterns
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
FACEBOOK_REGEX = re.compile(r"https?://(www\.)?facebook\.com/[a-zA-Z0-9_\-./]+")
LINKEDIN_REGEX = re.compile(r"https?://(www\.)?linkedin\.com/[a-zA-Z0-9_\-./]+")
PRIVACY_EMAIL_REGEX = re.compile(r"(privacy|dpo|data\.protection|gdpr|compliance)@", re.IGNORECASE)

# Excluded email list (unchanged)
excluded_emails = {
    "your@emailaddress.com",
    "info@domain.com",
    "name@domain.com",
    "example@domain.com",
    "example@yourdomain.com",
    "user@domain.com",
    "max@domain.com",
    "nama@domain.com",
    "hello@domain.com",
    "email@domain.com",
    "email@yourdomain.com",
    "username@domain.com",
    "guest@domain.com",
    "info@yourdomain.com",
    "myname@mydomain.com",
    "name@domain.me",
    "jane.doe@domain.com",
    "nexample@yourdomain.com",
    "agent@domain.com",
    "someone@mydomain.com",
    "username@gmail.com",
    "user@gmail.com",
    "your-email@bestcigarprices.com",
    "your-email@email.com",
    "your-email@isp.com",
    "your@email.com",
    "your@email.de",
    "youremail@domain.com",
    "youremail@gmail.com",
    "yourname@email.com",
    "yourname@yourwebsite.com",
    "example@mysite.com",
    "example@gmail.com",
    "example@subscribe.com",
    "example@mail.com",
    "example@me.com",
    "example@email.com",
    "example@idropnews.com",
    "example@yahoo.com",
    "contact@mysite.com",
    "info@mysite.com",
    "user@website.com",
    "abc@company.com",
    "abc@gmail.com",
    "abc@mail.com",
    "abc@xyz.com",
    "abc@yourmail.com",
    "demo@gmail.com",
    "dpo-google@google.com",
    "dpo@hotjar.com",
    "dpo@wordpress.org",
    "DPO@adobe.com",
    "dpo@altabir.es",
    "contact@yoursite.com",
    "help@yoursite.com",
    "creative@gmail.com",
    "email@abc.com",
    "email@address.com",
    "Email@company.com",
    "email@website.com",
    "email@email.com",
    "emil@yoursite.com",
    "enter.your@email.com",
    "enteryour@addresshere.com",
    "envato@mail.com",
    "example@domain-name.com",
    "example@yourmail.com",
    "exemple@gmail.com",
    "exemplo@gmail.com",
    "filler@godaddy.com",
    "first.last@email.com",
    "hello@company.com",
    "name@company.com",
    "name@email.com",
    "name@example.co.uk",
    "onum_company@mail.com",
    "sample@mail.com",
    "webmaster",
    "xyz@gmail.com",
    "you@business.com",
    "you@company.com",
    "you@domain.com",
    "abc@domain.com",
    "you@email.com",
    "you@youremail.com",
    "youremail@exampl.com",
    "yourmail@gmail.com",
    "yourname@yourcompany.com",
    "yourname@gmail.com",
    "someone@mydomain.com",
    "Gg@mail.gmail.com",
    "youremail@here.com",
    "yourname@hotmail.com",
    "you@gmail.com",
    "bili@mail.com",
    "example@domain.com",
    "address@somemail.com",
    "name@agency.com",
    "help@moz.com",
    "support@fb.com",
    "em@gmail.com",
    "you@company-email.com",
    "your-email@domain.com",
    "myemail@mailservice.com",
    "email@site.com",
    "privacy@domain.com",
    "data.protection@domain.com",
    "gdpr@domain.com",
    "compliance@domain.com"
}

# Save to simulated localStorage (JSON file)
def save_to_local_storage(data):
    with open("local_storage.json", "w") as f:
        json.dump(data, f)

def load_from_local_storage():
    if os.path.exists("local_storage.json"):
        with open("local_storage.json", "r") as f:
            return json.load(f)
    return []

# Fallback download if crash
def download_partial_results(results, filename="partial_results.csv"):
    if results:
        df = pd.DataFrame(results)
        df.to_csv(filename, index=False)
        st.download_button("Download Partial Data", df.to_csv(index=False), filename, "text/csv")

# --- Crawler Function to Fetch Up to User-Specified Pages ---
async def crawl_website(url, session, semaphore, status, results, email_df_container, unique_emails, max_pages):
    collected_emails = set()
    facebook_url = ""
    linkedin_url = ""
    visited_urls = set()
    urls_to_visit = deque([(url, 0)])  # (url, depth)
    max_depth = 3
    base_domain = urlparse(url).netloc

    # Common contact-related paths to prioritize
    priority_paths = ["/contact", "/about", "/team", "/contact-us", "/get-in-touch", "/support"]

    try:
        async with semaphore:
            # Add priority paths to crawl
            for path in priority_paths:
                full_url = urljoin(url, path)
                if full_url not in visited_urls:
                    urls_to_visit.append((full_url, 0))

            while urls_to_visit and len(visited_urls) < max_pages:
                current_url, depth = urls_to_visit.popleft()
                if current_url in visited_urls or depth > max_depth:
                    continue

                visited_urls.add(current_url)
                status['current'] = current_url

                try:
                    async with session.get(current_url, timeout=10) as response:
                        if response.status != 200:
                            continue
                        html = await response.text()
                        soup = BeautifulSoup(html, "html.parser")
                        for tag in soup(["script", "style", "noscript"]):
                            tag.decompose()
                        text = soup.get_text()
                        html_links = str(soup)

                        # Extract and filter emails
                        found_emails = EMAIL_REGEX.findall(text)
                        filtered_emails = {
                            email for email in found_emails
                            if email.lower() not in {e.lower() for e in excluded_emails}
                            and not PRIVACY_EMAIL_REGEX.search(email.lower())
                        }
                        collected_emails.update(filtered_emails)
                        unique_emails.update(filtered_emails)

                        # Extract social media links
                        if not facebook_url:
                            match_fb = FACEBOOK_REGEX.search(html_links)
                            if match_fb:
                                facebook_url = match_fb.group()

                        if not linkedin_url:
                            match_ln = LINKEDIN_REGEX.search(html_links)
                            if match_ln:
                                linkedin_url = match_ln.group()

                        # Find new links to crawl
                        for a_tag in soup.find_all("a", href=True):
                            href = a_tag["href"]
                            full_url = urljoin(current_url, href)
                            parsed_url = urlparse(full_url)
                            if parsed_url.netloc == base_domain and full_url not in visited_urls:
                                urls_to_visit.append((full_url, depth + 1))

                except Exception:
                    continue

    except Exception:
        pass
    finally:
        email_str = "No Email Found" if not collected_emails else " * ".join(sorted(collected_emails))
        facebook_str = facebook_url if facebook_url else "No Facebook Found"
        linkedin_str = linkedin_url if linkedin_url else "No LinkedIn Found"

        result = {
            "Website": url,
            "Emails": email_str,
            "Facebook URL": facebook_str,
            "LinkedIn URL": linkedin_str,
            "Pages Scanned": len(visited_urls)
        }

        results.append(result)
        save_to_local_storage(results)  # Save locally
        email_df_container.dataframe(pd.DataFrame(results))  # Live update

        status['scanned'] += 1

# --- Async Batch Processor ---
async def process_all_urls(urls, status, results, email_df_container, unique_emails, max_pages):
    semaphore = asyncio.Semaphore(5)
    async with aiohttp.ClientSession() as session:
        tasks = [
            crawl_website(url, session, semaphore, status, results, email_df_container, unique_emails, max_pages)
            for url in urls
        ]
        await asyncio.gather(*tasks)

# --- Prepare for download ---
def prepare_download_data(results):
    df = pd.DataFrame(results)
    output = BytesIO()
    df.to_csv(output, index=False)
    return output.getvalue(), "text/csv", "emails_social_links.csv"

# Main Streamlit app
uploaded_file = st.file_uploader("Upload CSV or Excel File With URLs", type=["csv", "xlsx"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
        st.success("File Loaded")
        st.write("**Preview:**", df.head())

        url_column = st.selectbox("Select URL Column", df.columns)
        max_pages = st.number_input("Maximum Pages to Scrape per Website", min_value=1, max_value=100, value=20, step=1)
        st.markdown("""
<style>
    * {margin: 0px; padding: 0px;}
</style>
<p style='margin:0; padding:0;'>
    The Number of maximum pages is directly proportional to the speed of Tool.
</p>
<p style='margin:0; padding:0;'>
    &nbsp;&nbsp;&nbsp;∴ Max&nbsp;Pages&nbsp;∝&nbsp;Tool&nbsp;Speed ∝ Emails Efficieny
</p>
<p style='color:var(--indigo-color);'>
    -Developer
</p>
""", unsafe_allow_html=True)


        if st.button("Start Extraction"):
            url_list = df[url_column].dropna().astype(str).tolist()
            total_urls = len(url_list)
            status = {
                "scanned": 0,
                "current": ""
            }
            unique_emails = set()  # Track unique emails across all websites
            results = []

            progress = st.progress(0)
            status_msg = st.empty()
            current_url_display = st.empty()
            estimate_time_display = st.empty()
            email_df_container = st.empty()
            valid_count_display = st.empty()

            start_time = time.time()

            async def update_ui():
                while status["scanned"] < total_urls:
                    elapsed = time.time() - start_time
                    percent = int((status["scanned"] / total_urls) * 100)
                    avg_time = elapsed / max(1, status["scanned"])
                    remaining = avg_time * (total_urls - status["scanned"])
                    mins, secs = divmod(int(remaining), 60)

                    # Real-time progress display
                    progress.progress(min(percent, 100))
                    status_msg.markdown(
                        f"Scanned Websites: **{status['scanned']} / {total_urls}**"
                    )
                    current_url_display.markdown(
                        f"Currently Scanning: `{status['current']}`"
                    )
                    valid_count_display.markdown(
                        f"Valid Emails Extracted: **{len(unique_emails)}**"
                    )
                    estimate_time_display.markdown(
                        f"Estimated Time Remaining: **{mins} min {secs} sec**"
                    )
                    await asyncio.sleep(0.5)

            async def main_runner():
                await asyncio.gather(
                    process_all_urls(url_list, status, results, email_df_container, unique_emails, max_pages),
                    update_ui()
                )

            with st.spinner("Extracting..."):
                try:
                    asyncio.run(main_runner())
                except Exception as e:
                    st.error("Crash detected. Auto-saving current results.")
                    download_partial_results(results)
                    raise e

            st.success(f"Completed: {len(unique_emails)} unique emails found in {status['scanned']} websites scanned.")

            st.markdown("---")
            st.subheader("Download Full Results")
            file_data, mime_type, file_name = prepare_download_data(results)
            st.download_button("Download CSV", file_data, file_name, mime_type)
        

    except Exception as e:
        st.error(f"Error while processing file: {e}")
else:
    st.write("")
