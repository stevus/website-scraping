from bs4 import BeautifulSoup
import re

def find_emails(content, text):

    soup = BeautifulSoup(content, "lxml")

    emails = set()

    # catch all emails in text
    emails_re = re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]{2,3}", text, re.I)
    emails.update(emails_re)

    # catch emails specifically in mailto links
    emails_bs4 = [a.text for a in soup.select('a[href^="mailto:"]')]
    emails.update(emails_bs4)

    return set(emails)