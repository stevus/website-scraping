from . import find_emails

def test_find_email():
    with open("extractemails/test_html.html", "r", encoding='utf-8') as f:
        html_content = f.read()
        assert len(find_emails(html_content, html_content)) == 4