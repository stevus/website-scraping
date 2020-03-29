# @link https://medium.com/swlh/how-to-scrape-email-addresses-from-a-website-and-export-to-a-csv-file-c5d1becbd1a0

import cgi
import csv
import os
import requests
import shutil

from . import find_emails
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
companies = {}
emails = {}
scraped = set()
unscraped = deque([])

# Read in CSV file of company name and contact info
with open(input_file, mode='r') as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    for row in csv_reader:
        if row[5] == 'AVOID':
            continue

        if row[2] in (None , '') and row[0] not in (None , ''):
            # get base url to limit crawler to business URLs only
            data = urlparse(row[1])
            base_url = '%s://%s' % (data.scheme, data.netloc)
            base_urls.add(base_url)
            # add seed URL to unscraped list
            unscraped.append(CompanyUrl(row[0], row[1]))

# Go through collection until no more unscraped URLs
while len(unscraped):

    co = unscraped.popleft()
    raw_url = co.url

    parsed_link = urlparse(raw_url)

    base_url = '%s://%s' % (parsed_link.scheme, parsed_link.netloc)
    url = '%s://%s%s' % (parsed_link.scheme, parsed_link.netloc, parsed_link.path)

    filtered_path = list(filter(lambda x: x != '' and x != None, parsed_link.path.split('/')))
    if len(filtered_path) > 1:
        # At the moment I dont care for links that are more than 1 folder deep
        continue

    if url in scraped:
        continue

    scraped.add(url)

    if base_url not in base_urls:
        continue

    print("Crawling URL %s" % url)

    try:
        response = requests.get(url, timeout=5)
    except (requests.exceptions.MissingSchema, requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
        companies[co.name] = 'ERROR'
        continue

    # dont crawl URLs that are text/html
    mimetype, options = cgi.parse_header(response.headers['Content-Type'])
    if mimetype != 'text/html':
        print('Unsupported mimetype: %s' % mimetype)
        continue

    # handle redirected URL in case the company changed domains
    if response.history:

        for resp in response.history:

            red_parsed_link = urlparse(response.url)
            red_clean_link = '%s://%s%s' % (red_parsed_link.scheme, red_parsed_link.netloc, red_parsed_link.path)
            red_base_url = '%s://%s' % (red_parsed_link.scheme, red_parsed_link.netloc)

            if parsed_link.netloc != red_parsed_link.netloc:
                # domain.com != newdomain.com
                print('URL for %s redirects from %s to %s' % (co.name, url, red_clean_link))
                base_urls.add(red_base_url)
                unscraped.append(CompanyUrl(co.name, red_clean_link))
            elif parsed_link.netloc == red_parsed_link.netloc and red_parsed_link.scheme != parsed_link.scheme:
                # http => https or https => http
                url = red_clean_link

    new_emails = find_emails(response.content, response.text)

    print('Found %s email for %s' % (len(new_emails), co.name))

    emails[co.name] = emails.get(co.name, set())
    emails[co.name].update(new_emails)

    soup = BeautifulSoup(response.content, "lxml")

    # find additional links on the page and add to unscraped if they qualify
    found_links = set()
    for anchor in soup.find_all("a", href=True):

        # cant do anything with these hrefs
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
        # read in error state if I've marked it so it can be ignored on the next run
        notes = companies.get(row[0], row[5])

        # dont override emails if they already exist in the CSV
        if row[2] not in (None , ''):
            coemails = row[2]
        else:
            coemails = '|'.join(emails.get(row[0], set()))

        # write the row
        write_row = {
            'Name': row[0],
            'URL': row[1],
            'Email': coemails,
            'Phone': None,
            'Contact': None,
            'Notes': notes
        }
        writer.writerow(write_row)

shutil.copyfile(temp_file, input_file)
os.remove(temp_file)
