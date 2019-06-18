from bs4 import BeautifulSoup
import urllib2

addresses = []
page_range = range(1, 27)
for page in page_range:

    html_page = urllib2.urlopen("https://www.taxexemptworld.com/organizations/sacramento-county-ca-california.asp?spg=%s" % (page), timeout=5)
    soup = BeautifulSoup(html_page, features="html.parser")

    nonprofit_rows = soup.select('.section-body table tbody tr')
    for row in nonprofit_rows:
        cols = row.findAll('td')
        addresses.push({
            address: cols[1].text,
            name: cols[0].select('a')[0].string
        })

print(addresses)
