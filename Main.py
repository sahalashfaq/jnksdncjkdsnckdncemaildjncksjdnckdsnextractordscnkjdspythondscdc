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
from urllib.parse import urljoin

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

# Load CSS (optional)
def load_css():
    try:
        with open("style.css") as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except:
        st.warning("No CSS loaded.")

load_css()

# Excluded email list
# List of emails to exclude (case-insensitive match)
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
    "email@site.com"
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
        st.download_button("⬇ Download Partial Data", df.to_csv(index=False), filename, "text/csv")

# --- Scraper Function ---
async def fetch_emails_from_url(url, session, semaphore, status, results, email_df_container):
    extra_paths = ["", "/contact", "/about", "/team"]
    collected_emails = set()
    facebook_url = ""
    linkedin_url = ""

    try:
        async with semaphore:
            for path in extra_paths:
                full_url = urljoin(url.strip(), path)
                status['current'] = full_url
                try:
                    async with session.get(full_url, timeout=10) as response:
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
                        }
                        collected_emails.update(filtered_emails)

                        if not facebook_url:
                            match_fb = FACEBOOK_REGEX.search(html_links)
                            if match_fb:
                                facebook_url = match_fb.group()

                        if not linkedin_url:
                            match_ln = LINKEDIN_REGEX.search(html_links)
                            if match_ln:
                                linkedin_url = match_ln.group()

                except:
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
            "LinkedIn URL": linkedin_str
        }

        results.append(result)
        save_to_local_storage(results)  # Save locally
        email_df_container.dataframe(pd.DataFrame(results))  # Live update

        if collected_emails:
           status['valid'] += 1
        status['scanned'] += 1


# --- Async Batch Processor ---
async def process_all_urls(urls, status, results, email_df_container):
    semaphore = asyncio.Semaphore(10)
    async with aiohttp.ClientSession() as session:
        tasks = [
            fetch_emails_from_url(url, session, semaphore, status, results, email_df_container)
            for url in urls
        ]
        await asyncio.gather(*tasks)

# --- Prepare for download ---
def prepare_download_data(results):
    df = pd.DataFrame(results)
    output = BytesIO()
    df.to_csv(output, index=False)
    return output.getvalue(), "text/csv", "emails_social_links.csv"


# # Recover previous session
# if st.sidebar.button("Recover Previous Data"):
#     prev_data = load_from_local_storage()
#     if prev_data:
#         st.success("Recovered previous session")
#         recovered_df = pd.DataFrame(prev_data)
#         st.dataframe(recovered_df)

#         # Download button for recovered data
#         st.download_button(
#             label="Download Recovered Data",
#             data=recovered_df.to_csv(index=False),
#             file_name="recovered_data.csv",
#             mime="text/csv"
#         )
#     else:
#         st.info("No previous data found.")


uploaded_file = st.file_uploader("Upload CSV or Excel File With URLs", type=["csv", "xlsx"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
        st.success("File Loaded")
        st.write("**Preview:**", df.head())

        url_column = st.selectbox("🔗 Select URL Column", df.columns)

        if st.button("Start Extraction"):
            url_list = df[url_column].dropna().astype(str).tolist()
            total_urls = len(url_list)
            status = {
                "valid": 0,      # emails found
                "scanned": 0,    # total websites visited
                "current": ""
            }

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
                    progress.progress(percent)
                    status_msg.markdown(
                        f"Scanned Websites: **{status['scanned']} / {total_urls}**"
                    )
                    current_url_display.markdown(
                        f"Currently Scanning: `{status['current']}`"
                    )
                    valid_count_display.markdown(
                        f"Valid Emails Extracted: **{status['valid']}**"
                    )
                    estimate_time_display.markdown(
                        f"Estimated Time Remaining: **{mins} min {secs} sec**"
                    )
                    await asyncio.sleep(0.5)


            async def main_runner():
                await asyncio.gather(
                    process_all_urls(url_list, status, results, email_df_container),
                    update_ui()
                )

            with st.spinner("Extracting..."):
                try:
                    asyncio.run(main_runner())
                except Exception as e:
                    st.error("Crash detected. Auto-saving current results.")
                    download_partial_results(results)
                    raise e

            valid_emails_count = sum(1 for r in results if r["Emails"] != "No Email Found")
            st.success(f"Completed: {status['valid']} emails found in {status['scanned']} websites scanned.")

            st.markdown("---")
            st.subheader("⬇ Download Full Results")
            file_data, mime_type, file_name = prepare_download_data(results)
            st.download_button("Download CSV", file_data, file_name, mime_type)

    except Exception as e:
        st.error(f"Error while processing file: {e}")
else:
    st.info("Please upload a file with website URLs to start.")

