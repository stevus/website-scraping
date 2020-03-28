# @link https://medium.com/swlh/how-to-scrape-email-addresses-from-a-website-and-export-to-a-csv-file-c5d1becbd1a0

import csv
import os
import re
import requests
import shutil

from bs4 import BeautifulSoup
from collections import deque
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit, urlparse

# I needed a way to group a url with a company
class CompanyUrl:

    def __init__(self, name, url):
        self.name = name
        self.url = url

input_file = 'extractemails/websites.csv'
temp_file = '/tmp/tmp_websites.csv'

base_urls = set()
emails = {}
scraped = set()
unscraped = deque([])

# Read in CSV file of company name and contact info
with open(input_file, mode='r') as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    for row in csv_reader:
        if row[2] in (None , '') and row[0] not in (None , ''):
            # get base url to limit crawler to business URLs only
            base_urls.add(row[1])
            # add seed URL to unscraped list
            unscraped.append(CompanyUrl(row[0], row[1]))

# Go through collection until no more unscraped URLs
while len(unscraped):

    co = unscraped.popleft()
    raw_url = co.url

    data = urlparse(raw_url)

    base_url = '%s://%s' % (data.scheme, data.netloc)
    url = '%s://%s%s' % (data.scheme, data.netloc, data.path)

    if url in scraped:
        continue

    scraped.add(url)

    if base_url not in base_urls:
        continue

    print("Crawling URL %s" % url)

    try:
        response = requests.get(url)
    except (requests.exceptions.MissingSchema, requests.exceptions.ConnectionError):
        continue

    new_emails = set(
        re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.com", response.text, re.I)
    )

    print('Found %s emails for %s' % (len(new_emails), co.name))

    emails[co.name] = emails.get(co.name, set())
    emails[co.name].update(new_emails)

    soup = BeautifulSoup(response.text, "lxml")

    # find additional links on the page and add to unscraped if they qualify
    found_links = set()
    for anchor in soup.find_all("a", href=True):

        if anchor['href'] is None or anchor['href'] == '#' or anchor['href'].endswith(".gz"):
            continue

        link = ''

        if anchor['href'].find(base_url) >= 0:
            link = anchor['href']

        if link.startswith("/"):
            link = base_url + link

        if link == '':
            continue

        if link not in unscraped and link not in scraped:
            parsed_link = urlparse(link)
            clean_link = '%s://%s%s' % (parsed_link.scheme, parsed_link.netloc, parsed_link.path)
            found_links.add(clean_link)

    for found_link in found_links:
        unscraped.append(CompanyUrl(co.name, found_link))

# Update emails to CSV file
fields = ['Name','URL','Email','Phone','Contact','Notes']
with open(input_file, "r") as infile, open(temp_file, "w") as outfile:

    reader = csv.reader(infile)
    next(reader, None)  # skip the headers
    writer = csv.DictWriter(outfile, fieldnames=fields)
    writer.writeheader()

    for row in reader:
        if row[2] not in (None , ''):
            coemails = row[2]
        else:
            coemails = '|'.join(emails.get(row[0], set()))

        write_row = {
            'Name': row[0],
            'URL': row[1],
            'Email': coemails,
            'Phone': None,
            'Contact': None,
            'Notes': None
        }
        writer.writerow(write_row)

shutil.copyfile(temp_file, input_file)
os.remove(temp_file)
